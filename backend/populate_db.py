import random
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models

fake = Faker()

print("Resetting database...")
models.Base.metadata.drop_all(bind=engine)
models.Base.metadata.create_all(bind=engine)


def create_users(db: Session):
    print("--- Seeding Users ---")
    fixed_users = [
        {"username": "admin", "role": models.RoleEnum.admin},
        {"username": "officer", "role": models.RoleEnum.loan_officer},
        {"username": "accountant", "role": models.RoleEnum.accountant},
    ]

    for u in fixed_users:
        if not db.query(models.User).filter_by(username=u["username"]).first():
            user = models.User(
                username=u["username"],
                password_hash="fake_hashed_password_123",
                role=u["role"],
            )
            db.add(user)

    for _ in range(5):
        profile = fake.simple_profile()
        if not db.query(models.User).filter_by(username=profile["username"]).first():
            user = models.User(
                username=profile["username"],
                password_hash=fake.sha256(),
                role=random.choice(list(models.RoleEnum)),
            )
            db.add(user)

    db.commit()


def create_loan_types(db: Session):
    print("--- Seeding Loan Types ---")
    types = [
        {"name": "Personal Loan", "max_amount": 50000, "max_tenure": 36, "base_interest_rate": 12.5},
        {"name": "Gold Loan", "max_amount": 100000, "max_tenure": 24, "base_interest_rate": 10.0},
        {"name": "Vehicle Loan", "max_amount": 500000, "max_tenure": 60, "base_interest_rate": 9.5},
        {"name": "Home Loan", "max_amount": 2000000, "max_tenure": 240, "base_interest_rate": 8.0},
    ]
    for t in types:
        if not db.query(models.LoanType).filter_by(name=t["name"]).first():
            db.add(models.LoanType(**t))
    db.commit()


def create_audit_logs(db: Session):
    print("--- Seeding Audit Logs ---")
    users = db.query(models.User).all()
    if not users:
        return

    actions = ["LOGIN", "CREATE_LOAN", "APPROVE_LOAN", "VIEW_REPORT", "UPDATE_BORROWER"]

    for _ in range(30):
        user = random.choice(users)
        log = models.AuditLog(
            user_id=user.id,
            action=random.choice(actions),
            details=f"Action performed on {fake.date()}",
            timestamp=fake.date_time_between(start_date="-1y", end_date="now"),
        )
        db.add(log)
    db.commit()


def create_borrowers_and_loans(db: Session):
    print("--- Seeding Borrowers, Loans, Repayments, Collateral & Ledger ---")
    loan_types = db.query(models.LoanType).all()

    max_borrowers = 10
    max_loans = 15
    loans_created = 0

    for _ in range(max_borrowers):
        income = random.uniform(3000, 15000)
        borrower = models.Borrower(
            name=fake.name(),
            address=fake.address().replace("\n", ", "),
            income=income,
            monthly_income=income,
            credit_score=random.randint(300, 850),
        )
        db.add(borrower)
        db.flush()

        if loans_created >= max_loans:
            continue

        remaining_loans = max_loans - loans_created
        possible_loans = min(3, remaining_loans)

        if possible_loans > 0 and random.random() < 0.8:
            num_loans = random.randint(1, possible_loans)
            for _ in range(num_loans):
                process_loan_logic(db, borrower.id, loan_types)
                loans_created += 1
                if loans_created >= max_loans:
                    break

    db.commit()


def process_loan_logic(db: Session, borrower_id: int, loan_types):
    loan_type = random.choice(loan_types)

    principal = round(random.uniform(5000, float(loan_type.max_amount)), 2)
    rate = loan_type.base_interest_rate

    term_options = [12, 24, 36, 48, 60, 120, 180, 240]
    term = min(random.choice(term_options), loan_type.max_tenure)

    created_at = fake.date_time_between(start_date="-2y", end_date="-1M")
    status_options = [
        models.LoanStatus.active,
        models.LoanStatus.closed,
        models.LoanStatus.pending,
        models.LoanStatus.rejected,
    ]
    status = random.choice(status_options)

    disbursed_on = None
    if status in [models.LoanStatus.active, models.LoanStatus.closed]:
        disbursed_on = created_at + timedelta(days=random.randint(1, 10))

    loan = models.Loan(
        borrower_id=borrower_id,
        loan_type_id=loan_type.id,
        principal=principal,
        interest_rate=rate,
        term_months=term,
        disbursed_on=disbursed_on,
        status=status,
        outstanding=principal,  # starts as full principal
        created_at=created_at,
    )
    db.add(loan)
    db.flush()

    if random.random() < 0.5:
        db.add(
            models.Collateral(
                loan_id=loan.id,
                type=random.choice(["Property", "Vehicle", "Gold", "Deposits"]),
                value=principal * 1.5,
                description=fake.sentence(),
                submitted_on=created_at,
            )
        )

    if disbursed_on:
        db.add(
            models.Ledger(
                loan_id=loan.id,
                type="disbursement",
                amount=principal,
                date=disbursed_on,
                balance_after=principal,
            )
        )
        generate_repayments(db, loan)


def generate_repayments(db: Session, loan: models.Loan):
    """
    EMI includes principal + interest, but loan.outstanding tracks ONLY principal.
    Each paid installment reduces outstanding by equal monthly principal.
    """
    principal = float(loan.principal)
    rate = loan.interest_rate

    total_interest = principal * (rate / 100) * (loan.term_months / 12)
    total_payable = principal + total_interest
    monthly_installment = round(total_payable / loan.term_months, 2)

    monthly_principal = round(principal / loan.term_months, 2)
    principal_outstanding = principal
    current_balance = principal_outstanding

    for i in range(1, loan.term_months + 1):
        due_date = loan.disbursed_on + timedelta(days=30 * i)
        now = datetime.now()

        repayment_status = "due"
        paid_amount = 0
        paid_on = None

        is_past_due = due_date < now
        should_pay = False

        if loan.status == models.LoanStatus.closed:
            should_pay = True
        elif loan.status == models.LoanStatus.active and is_past_due:
            if random.random() < 0.9:
                should_pay = True
            else:
                repayment_status = "overdue"

        if should_pay:
            repayment_status = "paid"
            paid_amount = monthly_installment
            paid_on = due_date + timedelta(days=random.randint(-2, 5))
            if paid_on > now:
                paid_on = now

        repayment = models.Repayment(
            loan_id=loan.id,
            due_date=due_date,
            amount=monthly_installment,
            paid_amount=paid_amount,
            paid_on=paid_on,
            status=repayment_status,
        )
        db.add(repayment)
        db.flush()

        if repayment_status == "paid":
            db.add(
                models.Receipt(
                    repayment_id=repayment.id,
                    receipt_number=fake.unique.bothify(text="REC-#####-????"),
                )
            )

            # reduce ONLY principal outstanding
            principal_outstanding = max(0, principal_outstanding - monthly_principal)
            current_balance = principal_outstanding

            db.add(
                models.Ledger(
                    loan_id=loan.id,
                    type="repayment",
                    amount=paid_amount,
                    date=paid_on,
                    balance_after=current_balance,
                )
            )

    loan.outstanding = max(0, principal_outstanding)


def populate():
    db = SessionLocal()
    try:
        create_users(db)
        create_loan_types(db)
        create_audit_logs(db)
        create_borrowers_and_loans(db)
        print("Database population completed successfully!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    populate()
