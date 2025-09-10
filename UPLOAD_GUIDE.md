# 📋 What to Upload to GitHub

## ✅ **Files You NEED to Upload**

Upload **ONLY** the `deploy_stuff` folder contents to your GitHub repository. Here's exactly what to include:

### **Essential Files from `deploy_stuff/`:**

```
deploy_stuff/
├── frontend/                    # ✅ UPLOAD - All frontend files
│   ├── index.html              # ✅ Main page (fixed paths)
│   ├── contact.html            # ✅ Contact page (EmailJS ready)
│   ├── projects.html           # ✅ Projects page
│   ├── meter-form-processor.html    # ✅ Demo tool
│   ├── single-occupancy-discount.html    # ✅ Demo tool
│   ├── secondary-suite-exemption.html    # ✅ Demo tool
│   ├── water-consumption-anomaly.html    # ✅ Demo tool
│   ├── sql-query-generator.html         # ✅ Demo tool (no backend)
│   ├── logo.png               # ✅ All images
│   ├── pfp2.png              
│   ├── CV.png                
│   ├── linkedin.png          
│   ├── github.png
│   ├── instagram.png
│   ├── gmail.png
│   ├── ubc.png               
│   ├── delta.png             
│   ├── jkp.png               
│   ├── microsoft.png         
│   ├── google.png
│   ├── ibm.png
│   ├── pfp.png
│   ├── Krishna Paudel Resume Aug 2025.pdf
│   └── Krishna Paudel Resume July 2025.pdf
├── vercel.json                 # ✅ UPLOAD - Vercel config
├── package.json                # ✅ UPLOAD - NPM config
├── .gitignore                  # ✅ UPLOAD - Git ignore rules
└── README.md                   # ✅ UPLOAD - Documentation
```

## ❌ **Files You DON'T Need to Upload**

**DO NOT upload these files from `deploy_stuff/`:**

```
deploy_stuff/
├── __init__.py                 # ❌ Python file
├── apt.txt                     # ❌ System dependencies
├── chatbot_data/               # ❌ Backend data
├── contact_backend.py          # ❌ Backend code
├── DEPLOYMENT_README.md        # ❌ Old deployment docs
├── llm_chatbot_backend.py      # ❌ Backend code
├── mcp_handler.py              # ❌ Backend code
├── mcp_instructions.json       # ❌ Backend config
├── Procfile                    # ❌ Railway config
├── railway.toml                # ❌ Railway config
├── requirements.txt            # ❌ Python dependencies
├── runtime.txt                 # ❌ Python runtime
├── setup_deployment.py         # ❌ Backend setup
└── SQL_App/                    # ❌ Entire SQL app directory
```

**DO NOT upload these files from main repo:**

```
main_repo/
├── __pycache__/                # ❌ Python cache
├── apt.txt                     # ❌ System deps
├── chatbot_data/               # ❌ Backend data
├── contact_backend.py          # ❌ Backend
├── dev_setup.py                # ❌ Development script
├── files/                      # ❌ Empty folder
├── frontend/                   # ❌ Duplicate (use deploy_stuff version)
├── llm_chatbot_backend.py      # ❌ Backend
├── local_config.py             # ❌ Local config
├── mcp_handler.py              # ❌ Backend
├── mcp_instructions.json       # ❌ Backend config
├── meter_form_backend.py       # ❌ Backend
├── NAVIGATION_FIXES.md         # ❌ Development docs
├── ocr_match_app.py            # ❌ Backend
├── Procfile                    # ❌ Railway config
├── railway.toml                # ❌ Railway config
├── requirements.txt            # ❌ Python deps
├── runtime.txt                 # ❌ Python runtime
├── secsuite_backend.py         # ❌ Backend
├── setup_env.py                # ❌ Development script
├── sod_form_backend.py         # ❌ Backend
├── SOD_form.py                 # ❌ Backend
├── SQL_App/                    # ❌ Entire SQL app
└── start.py                    # ❌ Development script
```

## 🚀 **Upload Commands**

```bash
# Navigate to deploy_stuff directory
cd deploy_stuff

# Initialize git repository
git init

# Add only the files we need
git add frontend/
git add vercel.json
git add package.json  
git add .gitignore
git add README.md

# Commit files
git commit -m "Initial commit: Portfolio website ready for deployment"

# Add remote origin (replace with your GitHub repo URL)
git remote add origin https://github.com/YOUR_USERNAME/portfolio-website.git

# Push to GitHub
git push -u origin main
```

## 📊 **Size Comparison**

- **Before**: ~100MB+ (entire repo with backends, SQL apps, cache files)
- **After**: ~5MB (just frontend files and config)

## ✅ **What This Gives You**

- ✅ **Clean repository** with only necessary files
- ✅ **Fast deployment** to Vercel
- ✅ **Professional portfolio** website
- ✅ **Contact form** with EmailJS
- ✅ **Custom domain** support
- ✅ **Mobile responsive** design

## 🎯 **Next Steps After Upload**

1. **Deploy to Vercel** using your GitHub repo
2. **Set up EmailJS** for contact form
3. **Add custom domain** in Vercel settings
4. **Test all pages** and functionality

Your portfolio will be live and professional! 🎉
