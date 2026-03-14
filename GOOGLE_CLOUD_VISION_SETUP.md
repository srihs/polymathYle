# Google Cloud Vision API Setup Guide

This guide will help you set up Google Cloud Vision API for OCR (handwriting recognition) in the PolymathYLE application upload feature.

---

## Prerequisites
- Google account
- Credit card (for Google Cloud - free tier available with $300 credit for new users)

---

## Step 1: Create Google Cloud Project

1. **Go to Google Cloud Console:**
   - Visit: https://console.cloud.google.com/

2. **Create a new project:**
   - Click on the project dropdown at the top
   - Click "New Project"
   - Project name: `polymathyle-ocr` (or any name you prefer)
   - Click "Create"
   - Wait for the project to be created (takes a few seconds)

3. **Select your project:**
   - Click on the project dropdown again
   - Select your newly created project

---

## Step 2: Enable Cloud Vision API

1. **Go to API Library:**
   - Visit: https://console.cloud.google.com/apis/library
   - OR: In the left sidebar, click "APIs & Services" → "Library"

2. **Search for Vision API:**
   - In the search box, type "Cloud Vision API"
   - Click on "Cloud Vision API" from the results

3. **Enable the API:**
   - Click the blue "Enable" button
   - Wait for it to be enabled (takes 10-20 seconds)

---

## Step 3: Create Service Account

1. **Go to Service Accounts:**
   - Visit: https://console.cloud.google.com/iam-admin/serviceaccounts
   - OR: Left sidebar → "IAM & Admin" → "Service Accounts"

2. **Create Service Account:**
   - Click "+ CREATE SERVICE ACCOUNT" at the top

3. **Fill in details:**
   - **Service account name:** `polymathyle-ocr-service`
   - **Service account ID:** (auto-filled) `polymathyle-ocr-service`
   - **Description:** `Service account for OCR in PolymathYLE application upload`
   - Click "CREATE AND CONTINUE"

4. **Grant permissions:**
   - In "Select a role" dropdown:
     - Search for "Cloud Vision"
     - Select **"Cloud Vision API User"**
   - Click "CONTINUE"

5. **Skip optional step:**
   - Click "DONE" (no need to grant users access)

---

## Step 4: Create and Download Credentials

1. **Find your service account:**
   - You should see your `polymathyle-ocr-service` in the list
   - Click on the email address (e.g., `polymathyle-ocr-service@polymathyle-ocr.iam.gserviceaccount.com`)

2. **Create a key:**
   - Click on the "KEYS" tab at the top
   - Click "ADD KEY" → "Create new key"

3. **Download JSON key:**
   - Select "JSON" format
   - Click "CREATE"
   - A JSON file will be downloaded automatically
   - **IMPORTANT:** Keep this file secure! It contains sensitive credentials.
   - Rename the file to something simple like: `google-vision-credentials.json`

---

## Step 5: Configure Credentials in PolymathYLE

You have **TWO options** for configuring the credentials:

### Option A: Store JSON file path (Recommended for development)

1. **Move the credentials file:**
   ```bash
   # Move the downloaded JSON file to your project directory
   # (Keep it outside of git - already in .gitignore)
   mv ~/Downloads/polymathyle-ocr-*.json /Users/sas/Repos/PolymathYLE/google-vision-credentials.json
   ```

2. **Update .env file:**
   Open `/Users/sas/Repos/PolymathYLE/.env` and add:
   ```bash
   # Google Cloud Vision API Credentials (for OCR)
   GOOGLE_APPLICATION_CREDENTIALS=/Users/sas/Repos/PolymathYLE/google-vision-credentials.json
   ```

### Option B: Store JSON content directly (Recommended for production)

1. **Copy the entire JSON content:**
   - Open the downloaded JSON file in a text editor
   - Copy ALL the content (including the curly braces)

2. **Update .env file:**
   Open `/Users/sas/Repos/PolymathYLE/.env` and add:
   ```bash
   # Google Cloud Vision API Credentials (for OCR)
   GOOGLE_CLOUD_CREDENTIALS='{"type":"service_account","project_id":"polymathyle-ocr",...}'
   ```

   **IMPORTANT:**
   - Wrap the JSON in single quotes
   - Make sure it's all on one line
   - Don't add any line breaks in the JSON

---

## Step 6: Update .gitignore (Already Done)

The file `google-vision-credentials.json` should already be in `.gitignore` to prevent committing credentials to git.

To verify:
```bash
cat /Users/sas/Repos/PolymathYLE/.gitignore | grep google-vision
```

If not found, add this line to `.gitignore`:
```
google-vision-credentials.json
```

---

## Step 7: Restart Django Server

After configuring credentials, restart your Django development server:

```bash
# Stop the server (Ctrl+C)
# Then restart:
env/bin/python manage.py runserver
```

---

## Step 8: Test OCR Functionality

1. **Navigate to Upload Application page:**
   - Go to: http://localhost:8000/students/applications/upload/

2. **Upload a scanned form:**
   - Upload one of your scanned application forms

3. **Click "Extract Data" button:**
   - The button should appear after uploading
   - Click it and wait (may take 2-5 seconds)

4. **Verify results:**
   - Form fields should auto-populate with extracted data
   - Check if the data is correct
   - Manually correct any errors
   - Save the application

---

## Troubleshooting

### Error: "Invalid JSON in GOOGLE_CLOUD_CREDENTIALS"
**Cause:** The JSON format is incorrect in the .env file

**Solutions:**
- Make sure the entire JSON is on ONE line
- Make sure it's wrapped in single quotes: `'{ ... }'`
- No line breaks within the JSON
- Use Option A (file path) instead for easier setup

### Error: "Permission denied"
**Cause:** Service account doesn't have Vision API permissions

**Solution:**
1. Go to IAM & Admin → Service Accounts
2. Click on your service account
3. Click "Permissions" tab
4. Make sure "Cloud Vision API User" role is assigned

### Error: "API not enabled"
**Cause:** Cloud Vision API is not enabled for the project

**Solution:**
1. Go to APIs & Services → Library
2. Search for "Cloud Vision API"
3. Click "Enable"

### Error: "Quota exceeded"
**Cause:** You've exceeded the free tier limit

**Free Tier Limits:**
- 1,000 requests per month for handwriting detection
- After that: $1.50 per 1,000 images

**Solution:**
- Check usage in: APIs & Services → Dashboard
- Enable billing if needed
- Consider caching results to reduce API calls

---

## Cost Information

**Free Tier (New Users):**
- $300 credit for 90 days
- 1,000 Vision API requests/month free

**After Free Tier:**
- Document Text Detection (handwriting): $1.50 per 1,000 images
- First 1,000 requests/month: Free

**For PolymathYLE:**
If you process 100 applications per month:
- Cost: $0 (within free tier)

If you process 2,000 applications per month:
- Cost: $1.50 (1,000 free + 1,000 paid)

---

## Security Best Practices

1. ✅ **Never commit credentials to git**
   - Already configured in .gitignore

2. ✅ **Use environment variables**
   - Already using .env file

3. ✅ **Restrict service account permissions**
   - Only gave "Cloud Vision API User" role (minimum required)

4. ✅ **Rotate credentials periodically**
   - Create new key every 90 days
   - Delete old keys

5. ✅ **Monitor API usage**
   - Check Google Cloud Console → APIs & Services → Dashboard
   - Set up budget alerts

---

## What the OCR Service Does

Once configured, the OCR service will:

1. **Read handwritten text** from scanned application forms
2. **Identify form fields** by matching labels (e.g., "NAME WITH INITIALS")
3. **Extract values** next to each label
4. **Parse and format** data:
   - Dates: Convert to YYYY-MM-DD format
   - Phone numbers: Format as Sri Lankan numbers
   - Gender: Normalize to MALE/FEMALE
5. **Auto-populate form fields** in the upload interface
6. **Allow manual corrections** before saving

---

## Next Steps

After setting up credentials:

1. ✅ Test OCR with a sample scanned application
2. ✅ Verify extracted data accuracy
3. ✅ Process your backlog of paper applications
4. ⚠️ Monitor API usage and costs
5. ⚠️ Set up billing alerts in Google Cloud Console

---

## Support

If you encounter issues:

1. **Check Django logs:**
   ```bash
   # Look for OCR-related errors
   tail -f /path/to/django/logs
   ```

2. **Check browser console:**
   - Open Developer Tools (F12)
   - Check Console tab for JavaScript errors

3. **Check Google Cloud logs:**
   - Go to: https://console.cloud.google.com/logs
   - Filter by "Cloud Vision API"

---

## Summary

✅ Create Google Cloud project
✅ Enable Cloud Vision API
✅ Create service account with "Cloud Vision API User" role
✅ Download JSON credentials
✅ Add to .env file (file path OR JSON content)
✅ Restart Django server
✅ Test OCR functionality

The setup should take about 10-15 minutes. Once complete, the OCR will automatically extract handwritten text from scanned applications!
