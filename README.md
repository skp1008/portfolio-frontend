# Krishna Paudel - Portfolio Website

A modern, responsive portfolio website showcasing my work as a Finance Intern and Data Science student at UBC.

## 🌟 Features

- **Modern Design**: Clean, professional interface with animated tech background
- **Responsive**: Optimized for desktop, tablet, and mobile devices
- **Interactive**: Smooth animations and hover effects
- **Portfolio Showcase**: Detailed project descriptions and work experience
- **Contact Form**: EmailJS integration for contact functionality

## 🚀 Live Demo

Visit the live website at: [Your Domain Here]

## 📁 Project Structure

```
deploy_stuff/
├── frontend/
│   ├── index.html              # Main portfolio page (renamed from website2.html)
│   ├── contact.html            # Contact page with EmailJS
│   ├── projects.html           # Projects showcase
│   ├── meter-form-processor.html    # City of Delta tool (demo)
│   ├── single-occupancy-discount.html    # City of Delta tool (demo)
│   ├── secondary-suite-exemption.html    # City of Delta tool (demo)
│   ├── water-consumption-anomaly.html    # City of Delta tool (demo)
│   ├── sql-query-generator.html         # SQL tool (demo)
│   ├── logo.png               # Site logo
│   ├── pfp2.png              # Profile picture
│   ├── CV.png                # Resume icon
│   ├── linkedin.png          # Social media icons
│   ├── github.png
│   ├── instagram.png
│   ├── gmail.png
│   ├── ubc.png               # University logo
│   ├── delta.png             # City of Delta logo
│   ├── jkp.png               # JKP logo
│   ├── microsoft.png         # Certification logos
│   ├── google.png
│   ├── ibm.png
│   └── [resume files].pdf    # PDF resumes
├── vercel.json               # Vercel deployment configuration
├── package.json              # NPM package configuration
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

## 🛠️ Technologies Used

- **HTML5**: Semantic markup
- **CSS3**: Modern styling with animations
- **JavaScript**: Interactive functionality
- **EmailJS**: Contact form functionality
- **Google Fonts**: Inter font family
- **Responsive Design**: Mobile-first approach

## 📧 Setting Up Contact Form (EmailJS)

1. **Go to [EmailJS.com](https://www.emailjs.com/)** and sign up
2. **Create an email service**:
   - Connect your Gmail account
   - Note down your **Service ID**
3. **Create an email template**:
   - Template ID: `template_contact` (or your preferred name)
   - Add template variables: `{{from_name}}`, `{{from_company}}`, `{{subject}}`, `{{message}}`
   - Note down your **Template ID**
4. **Get your Public Key** from Account settings
5. **Update `frontend/contact.html`**:
   - Replace `YOUR_PUBLIC_KEY` with your actual public key
   - Replace `YOUR_SERVICE_ID` with your service ID
   - Replace `YOUR_TEMPLATE_ID` with your template ID

## 🚀 Deployment to Vercel

### Step 1: Create GitHub Repository

1. **Create a new repository** on GitHub:
   - Repository name: `portfolio-website` (or your preferred name)
   - Make it **Public** (required for free Vercel deployment)

2. **Upload this deploy_stuff folder**:
   ```bash
   # Navigate to deploy_stuff directory
   cd deploy_stuff
   
   # Initialize git repository
   git init
   
   # Add all files
   git add .
   
   # Commit files
   git commit -m "Initial commit: Portfolio website ready for deployment"
   
   # Add remote origin (replace with your GitHub repo URL)
   git remote add origin https://github.com/YOUR_USERNAME/portfolio-website.git
   
   # Push to GitHub
   git push -u origin main
   ```

### Step 2: Deploy to Vercel

1. **Go to [Vercel.com](https://vercel.com)** and sign up/login
2. **Click "New Project"**
3. **Import your GitHub repository**
4. **Configure deployment**:
   - Framework Preset: **Other** (or leave as auto-detected)
   - Root Directory: `./` (default)
   - Build Command: Leave empty (static site)
   - Output Directory: Leave empty (static site)
5. **Click "Deploy"**

### Step 3: Add Custom Domain

1. **In your Vercel dashboard**, go to your project
2. **Click "Settings"** → **"Domains"**
3. **Add your domain** and follow DNS configuration instructions

## 📱 Responsive Design

The website is fully responsive and optimized for:
- **Desktop**: 1200px+ (full experience)
- **Tablet**: 768px - 1199px (adapted layout)
- **Mobile**: 320px - 767px (mobile-optimized)

## ✅ What's Working

- ✅ **Main portfolio page** with all sections
- ✅ **Projects showcase** page
- ✅ **Contact page** with EmailJS integration
- ✅ **All City of Delta tool pages** (as demos)
- ✅ **Responsive design** for all devices
- ✅ **Social media links** and resume downloads

## ❌ What's Disabled

- ❌ **SQL Query Generator** chat functionality (backend removed)
- ❌ **Form processing tools** (backend removed)
- ❌ **Backend-dependent features**

## 🔧 Local Development

To test your site locally:

```bash
# Using Python
python -m http.server 8000

# Using Node.js
npx serve frontend

# Using PHP
php -S localhost:8000 -t frontend
```

Then visit `http://localhost:8000`

## 📧 Contact

- **Email**: jaskp1008@gmail.com
- **LinkedIn**: [Krishna Paudel](https://www.linkedin.com/in/krishna-paudel-4705a3262/)
- **GitHub**: [skp1008](https://github.com/skp1008)
- **Instagram**: [krishna.1008](https://www.instagram.com/krishna.1008/)

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

**Built with ❤️ by Krishna Paudel**
