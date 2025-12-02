# PostgreSQL Views, Stored Procedures, and Triggers

This document contains the SQL definitions for Views, Stored Procedures, and Triggers designed for the Loan Management System.

## 1. Views

### `v_borrower_portfolio`

Provides a comprehensive view of each borrower's financial standing.

```sql
CREATE OR REPLACE VIEW v_borrower_portfolio AS
SELECT
    b.id AS borrower_id,
    b.name AS borrower_name,
    b.credit_score,
    COUNT(l.id) AS total_loans_count,
    COALESCE(SUM(l.principal), 0) AS total_principal_disbursed,
    COALESCE(SUM(l.outstanding), 0) AS total_outstanding_amount,
    COALESCE(SUM(l.principal) - SUM(l.outstanding), 0) AS total_repaid_principal
FROM
    borrowers b
LEFT JOIN
    loans l ON b.id = l.borrower_id
GROUP BY
    b.id, b.name, b.credit_score;
```

### `v_overdue_repayments`

Helps loan officers track missed payments.

```sql
CREATE OR REPLACE VIEW v_overdue_repayments AS
SELECT
    r.id AS repayment_id,
    l.id AS loan_id,
    b.name AS borrower_name,
    b.address AS borrower_address,
    r.due_date,
    r.amount AS amount_due,
    EXTRACT(DAY FROM (CURRENT_DATE - r.due_date)) AS days_overdue
FROM
    repayments r
JOIN
    loans l ON r.loan_id = l.id
JOIN
    borrowers b ON l.borrower_id = b.id
WHERE
    r.status IN ('due', 'overdue')
    AND r.due_date < CURRENT_DATE;
```

### `v_loan_performance`

Analytics view for management.

```sql
CREATE OR REPLACE VIEW v_loan_performance AS
SELECT
    lt.name AS loan_type,
    COUNT(l.id) AS total_active_loans,
    COALESCE(SUM(l.outstanding), 0) AS total_outstanding_exposure,
    ROUND(AVG(l.interest_rate)::numeric, 2) AS avg_interest_rate
FROM
    loan_types lt
LEFT JOIN
    loans l ON lt.id = l.loan_type_id AND l.status = 'active'
GROUP BY
    lt.name;
```

## 2. Stored Procedures

### `sp_approve_and_disburse_loan`

Approves a pending loan, sets it to active, and generates the repayment schedule.

```sql
CREATE OR REPLACE PROCEDURE sp_approve_and_disburse_loan(
    p_loan_id INT,
    p_user_id INT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_loan_record RECORD;
    v_monthly_emi NUMERIC(10,2);
    v_total_interest NUMERIC(10,2);
    v_repayment_date DATE;
    v_disbursed_date TIMESTAMP;
    i INT;
BEGIN
    -- 1. Check if loan exists, is pending, AND LOCK THE ROW
    -- The 'FOR UPDATE' prevents other transactions from modifying this row
    -- until this transaction finishes.
    SELECT * INTO v_loan_record
    FROM loans
    WHERE id = p_loan_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Loan ID % not found', p_loan_id;
    END IF;

    IF v_loan_record.status != 'pending' THEN
        RAISE EXCEPTION 'Loan is not in pending status (Current: %)', v_loan_record.status;
    END IF;

    -- Capture current time once to ensure consistency
    v_disbursed_date := CURRENT_TIMESTAMP;

    -- 2. Update status to active
    UPDATE loans
    SET status = 'active',
        disbursed_on = v_disbursed_date,
        outstanding = principal
    WHERE id = p_loan_id;

    -- 3. Calculate EMI (Using NUMERIC for precision)
    -- Formula: (P + (P * R * T_years)/100) / T_months
    -- Note: Assuming interest_rate is annual.

    v_total_interest := (v_loan_record.principal * v_loan_record.interest_rate * (v_loan_record.term_months::NUMERIC / 12)) / 100;
    v_monthly_emi := (v_loan_record.principal + v_total_interest) / v_loan_record.term_months;

    -- 4. Generate Schedule
    FOR i IN 1..v_loan_record.term_months LOOP
        -- Fix date drift: Add 'i' months to the original disbursement date
        v_repayment_date := (v_disbursed_date + (i || ' month')::INTERVAL)::DATE;

        INSERT INTO repayments (loan_id, due_date, amount, paid_amount, status)
        VALUES (
            p_loan_id,
            v_repayment_date,
            ROUND(v_monthly_emi, 2),
            0,  --
            'due'
        );
    END LOOP;

    -- 5. Insert disbursement record into ledger
    INSERT INTO ledger (loan_id, type, amount, balance_after)
    VALUES (p_loan_id, 'disbursement', v_loan_record.principal, v_loan_record.principal);

    -- 6. Log action
    INSERT INTO audit_logs (user_id, action, details)
    VALUES (p_user_id, 'LOAN_DISBURSED', 'Loan ID ' || p_loan_id || ' disbursed. Status: Active.');

END;
$$;
```

CALL sp_approve_and_disburse_loan(4, 9)

## 3. Triggers

### `trg_enforce_active_loan_limit`

Prevents a borrower from having more than 3 active loans.

```sql
CREATE OR REPLACE FUNCTION fn_enforce_active_loan_limit()
RETURNS TRIGGER AS $$
DECLARE
    v_active_count INT;
BEGIN
    SELECT COUNT(*) INTO v_active_count
    FROM loans
    WHERE borrower_id = NEW.borrower_id AND status = 'active';

    IF v_active_count >= 3 THEN
        RAISE EXCEPTION 'Borrower % already has % active loans. Limit is 3.', NEW.borrower_id, v_active_count;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_enforce_active_loan_limit
BEFORE INSERT ON loans
FOR EACH ROW
EXECUTE FUNCTION fn_enforce_active_loan_limit();
```

INSERT INTO loans (borrower_id, principal, interest_rate, term_months, status)
VALUES (
19,  
 50000.00,  
 10.5,  
 12, 'pending'  
);

### `trg_auto_update_loan_status`

Automatically closes the loan when outstanding balance reaches zero.

```sql
CREATE OR REPLACE FUNCTION fn_auto_update_loan_status()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.outstanding <= 0 AND OLD.outstanding > 0 THEN
        NEW.status := 'closed';
        NEW.outstanding := 0; -- Ensure it doesn't go negative
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_auto_update_loan_status
BEFORE UPDATE ON loans
FOR EACH ROW
EXECUTE FUNCTION fn_auto_update_loan_status();
```
