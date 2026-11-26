# 🛒 NovaCart – E-Commerce Website

NovaCart is a full-stack e-commerce web application developed using Python Flask, SQLite, HTML, CSS, and JavaScript. It provides a simple online shopping experience with customer authentication, product management, shopping cart, checkout, and an admin dashboard.

## 🚀 Features

### Customer Features
- User registration and login
- Browse and search products
- Product details
- Shopping cart management
- Checkout with Cash on Delivery
- View order history and order details

### Admin Features
- Admin authentication
- Add, edit, and delete products
- Manage customer orders
- Update order status
- Admin dashboard

## 🛠️ Technologies Used

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, Flask
- **Database:** SQLite
- **Tools:** Visual Studio Code, Git, GitHub

## 📁 Project Structure

```text
NovaCart/
├── app.py
├── config.py
├── database.py
├── requirements.txt
├── .env.example
├── .gitignore
├── templates/
├── static/
│   ├── css/
│   └── js/
└── instance/
```

## ⚙️ Installation and Setup

1. Clone the repository:

```bash
git clone https://github.com/gnapikakota-dotcom/NovaCart.git
```

2. Open the project folder:

```bash
cd NovaCart
```

3. Create a virtual environment:

```bash
python -m venv venv
```

4. Activate the environment on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

5. Install dependencies:

```bash
pip install -r requirements.txt
```

6. Create a `.env` file using `.env.example` and configure your environment variables.

7. Run the application:

```bash
python app.py
```

8. Open your browser:

```text
http://127.0.0.1:5000/
```

## 🔐 Security

- Passwords are stored using password hashing.
- Environment variables are managed through `.env`.
- Sensitive files and local database files are excluded from Git.

## 🔮 Future Enhancements

- Online payment gateway integration
- Product reviews and ratings
- Wishlist functionality
- Email notifications
- Order tracking

## 👩‍💻 Developer

**Gnapika Kota**

GitHub: https://github.com/gnapikakota-dotcom

---

⭐ If you find this project useful, consider giving the repository a star!