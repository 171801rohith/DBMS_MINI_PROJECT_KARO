# Loan Management System

A comprehensive Loan Management System built with a modern tech stack, designed to streamline the process of managing loans, borrowers, and repayments. This project consists of a **FastAPI** backend and a **React** frontend.

## 🚀 Tech Stack

### Backend
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) - High-performance, easy-to-learn, fast to code, ready for production.
- **Database:** PostgreSQL
- **ORM:** [SQLAlchemy](https://www.sqlalchemy.org/)
- **Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
- **Authentication:** JWT (JSON Web Tokens) with `python-jose` and `passlib`.
- **Validation:** Pydantic

### Frontend
- **Framework:** [React](https://react.dev/)
- **Build Tool:** [Vite](https://vitejs.dev/)
- **Routing:** React Router DOM
- **Charts:** Recharts
- **Icons:** Lucide React
- **Styling:** CSS Modules / Standard CSS

## 📂 Project Structure

```
DBMS-MP-LoanManagement/
├── backend/                # FastAPI Backend
│   ├── app/
│   │   ├── routers/        # API Routes
│   │   ├── models.py       # Database Models
│   │   ├── schemas.py      # Pydantic Schemas
│   │   └── main.py         # Application Entry Point
│   ├── db-migrations/      # Alembic Migrations
│   ├── populate_db.py      # Script to seed database
│   └── requirements.txt    # Python Dependencies
│
└── frontend/               # React Frontend
    ├── src/
    │   ├── components/     # Reusable UI Components
    │   ├── App.jsx         # Main App Component
    │   └── main.jsx        # Entry Point
    └── package.json        # Node Dependencies
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- Node.js & npm
- PostgreSQL installed and running

### 1. Backend Setup

Navigate to the backend directory:
```bash
cd backend
```

Create a virtual environment:
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

**Environment Variables:**
Create a `.env` file in the `backend` directory. You can use the `.env.example` if available, or add the following:
```env
DATABASE_URL=postgresql://user:password@localhost/dbname
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Run Database Migrations:
```bash
alembic upgrade head
```

(Optional) Seed the Database:
```bash
python populate_db.py
```

Start the Server:
```bash
uvicorn app.main:app --reload
```
The backend API will be available at `http://localhost:8000`.
Interactive API docs: `http://localhost:8000/docs`.

### 2. Frontend Setup

Open a new terminal and navigate to the frontend directory:
```bash
cd frontend
```

Install dependencies:
```bash
npm install
```

Start the Development Server:
```bash
npm run dev
```
The application will be available at `http://localhost:5173` (or the port shown in the terminal).

## ✨ Features

- **User Authentication:** Secure login and registration for administrators/users.
- **Loan Management:** Create, view, update, and delete loan records.
- **Borrower Management:** Manage borrower profiles and details.
- **Repayment Tracking:** Track loan repayments and generate receipts.
- **Dashboard:** Visual analytics using charts to monitor loan statistics.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
