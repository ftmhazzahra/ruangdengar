# 🔐 Password Reset Feature - Deployment Guide

**Date:** January 4, 2026  
**Status:** ✅ Ready for Production  
**Feature:** Forgot Password & Reset Password

---

## 📋 What's New

### **Features Added:**
- ✅ Forgot Password page (/forgot-password/)
- ✅ Reset Password page with token validation (/reset-password/)
- ✅ Email notification dengan reset link
- ✅ Token expiry validation (24 hours)
- ✅ Password strength validation (8+ chars, huruf + angka)
- ✅ Security: Token is cleared after password reset

### **Files Changed/Created:**

#### **Models** (users/models.py)
- `password_reset_token` - Menyimpan reset token
- `password_reset_token_created_at` - Timestamp untuk validasi expiry

#### **Forms** (users/forms.py)
- `ForgotPasswordForm` - Email validation
- `ResetPasswordForm` - Password validation dengan strength check

#### **Views** (users/views.py)
- `forgot_password_view()` - Generate token & kirim email
- `reset_password_view()` - Validate token & reset password

#### **Templates**
- `templates/users/forgot_password.html` - Form lupa password
- `templates/users/reset_password.html` - Form reset password
- `templates/emails/password_reset.html` - Email template
- `templates/users/login_new.html` - Updated forgot password link
- `templates/users/login.html` - Updated forgot password link

#### **URLs** (users/urls.py)
- `/forgot-password/` → forgot_password_view
- `/reset-password/` → reset_password_view

#### **Migration**
- `users/migrations/0031_add_password_reset_fields.py` - Add 2 new fields

---

## 🚀 Deployment Steps

### **1. Push Code ke Git**
```bash
cd "c:\Downloads\RUANG-DENGAR1-main\RUANG-DENGAR1-main\ruangdengar - Copy"

# Add changes
git add .

# Commit with message
git commit -m "feat: implement forgot password & reset password feature"

# Push to remote
git push origin main  # atau branch Anda
```

### **2. SSH ke VPS**
```bash
ssh root@157.66.34.207
# Password: Tracer2025-ruangdengar!
```

### **3. Pull Code Terbaru**
```bash
cd /var/www/ruangdengar
git pull origin main
```

### **4. Activate Virtual Environment & Install Dependencies**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### **5. Run Migration**
```bash
python manage.py migrate users
# Output: Applying users.0031_add_password_reset_fields... OK
```

### **6. Collect Static Files** (if needed)
```bash
python manage.py collectstatic --noinput
```

### **7. Restart Services**
```bash
# Restart Gunicorn
sudo systemctl restart gunicorn

# Restart Nginx (if needed)
sudo systemctl restart nginx

# Verify status
sudo systemctl status gunicorn
sudo systemctl status nginx
```

### **8. Test Production**
```bash
# Check logs
sudo tail -f /var/log/gunicorn/error.log
sudo tail -f /var/log/nginx/error.log

# Test email sending (manual test via web)
# 1. Go to https://ruangdengar.cloud/login/
# 2. Click "Lupa password?"
# 3. Input registered email
# 4. Check email inbox untuk reset link
```

---

## 📧 Email Configuration (Important!)

### **Production Email Setup:**

Must be configured in `.env` at VPS:

```bash
# Gmail SMTP Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# From address
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

### **How to Generate Gmail App Password:**
1. Go to https://myaccount.google.com/security
2. Enable 2-Factor Authentication
3. Create "App Password" for "Mail" app
4. Use that 16-character password as `EMAIL_HOST_PASSWORD`

---

## 🧪 Testing Checklist

- [ ] Server running without errors
- [ ] Forgot password page loads
- [ ] Email sends successfully
- [ ] Reset link in email is valid
- [ ] Reset password page loads with valid token
- [ ] Password reset works
- [ ] Login with new password works
- [ ] Token expired after 24 hours
- [ ] Invalid token shows error

---

## 🔒 Security Notes

✅ Token validation: 24 hour expiry  
✅ Password strength: min 8 chars + letters + numbers  
✅ Token cleared after successful reset  
✅ Email validation before sending  
✅ CSRF protection enabled  

---

## 📝 Rollback (if needed)

```bash
# Rollback migration
python manage.py migrate users 0030_customuser_email_verification_sent_at_and_more

# Or revert git commit
git revert <commit-hash>
git push origin main
```

---

## 📞 Support

If any issues:
1. Check `/var/log/gunicorn/error.log`
2. Check `/var/log/nginx/error.log`
3. Verify `.env` file has all required variables
4. Ensure PostgreSQL running: `sudo systemctl status postgresql`

---

**Deployment Date:** [To be filled]  
**Deployed By:** [To be filled]  
**Status:** [Testing/Production]
