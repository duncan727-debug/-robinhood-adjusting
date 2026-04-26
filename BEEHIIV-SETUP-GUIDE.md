# Beehiiv Setup Guide for South Florida Property Intelligence Report

**Goal:** Set up Beehiiv to receive newsletter subscribers from your website form, segment them by type (Homeowners / Service Providers / Real Estate Pros), and send tailored briefs.

---

## Step 1: Sign Up for Beehiiv

1. Go to **[beehiiv.com](https://beehiiv.com)**
2. Click **"Get Started"** or **"Sign Up"**
3. Enter your email (recommend: `duncanlittlejohnjr@gmail.com`)
4. Create a password
5. Complete the signup flow

---

## Step 2: Create Your Publication

Once logged in:

1. Click **"Create Publication"** (or **"New Publication"**)
2. **Publication Name:** `South Florida Property Intelligence Report`
3. **Description:** `Daily market intelligence, regulatory updates, and claims landscape for South Florida property professionals`
4. **Category:** Insurance / Real Estate (pick what fits best)
5. **Click "Create"**

You'll be taken to your publication dashboard.

---

## Step 3: Set Up Subscriber Segments

Segments allow you to send different content to different subscriber types.

### Navigate to Segments:
1. Go to **Settings** (gear icon, lower left)
2. Click **"Segments"** or **"Audience"**
3. Click **"Create Segment"** or **"New Segment"**

### Create Segment 1: Homeowners
- **Name:** `Homeowners`
- **Description:** `Residential property owners and homeowners`
- **Click "Create"** (save the segment ID when it appears)

### Create Segment 2: Service Providers
- **Name:** `Service Providers`
- **Description:** `Contractors, restoration specialists, HVAC, plumbing, and claims professionals`
- **Click "Create"** (save the segment ID)

### Create Segment 3: Real Estate Professionals
- **Name:** `Real Estate Professionals`
- **Description:** `Real estate agents, investors, property managers, and development professionals`
- **Click "Create"** (save the segment ID)

---

## Step 4: Generate Your API Key

1. Go to **Settings** (gear icon)
2. Look for **"API"**, **"Integrations"**, or **"Webhooks"**
3. Find or generate your **API Key**
4. Copy it and save it somewhere secure
5. Also note your **Publication ID** (visible in the URL bar or settings)

---

## Step 5: Custom Fields (to store subscriber type)

1. Still in **Settings**, look for **"Custom Fields"** or **"Audience Fields"**
2. Click **"Add Custom Field"**
3. **Field Name:** `Subscriber Type`
4. **Field Type:** `Single Select` or `Text`
5. **Options:** 
   - Homeowner
   - Service Provider
   - Real Estate Professional
   - Other
6. **Click "Save"**

Save the **field ID** that appears.

---

## Step 6: Information to Share Back

Once complete, reply with these details:

```
Beehiiv Setup Complete:
- Email: [your beehiiv login email]
- API Key: [your API key — keep this secret!]
- Publication ID: [your publication ID]
- Segment IDs:
  - Homeowners: [ID]
  - Service Providers: [ID]
  - Real Estate Professionals: [ID]
- Custom Field ID (Subscriber Type): [ID]
```

---

## Step 7 (Optional): Set Up Your First Email/Brief

While you're in Beehiiv, you can:

1. Go to **"Posts"** or **"Emails"**
2. Click **"New Post"** or **"New Email"**
3. Write or paste content from your April 24 brief
4. Select which segment(s) to send to
5. Schedule or send

This confirms the system is working before I integrate the form.

---

## Troubleshooting Tips

- **Can't find API settings?** Check **Settings > Integrations** or **Settings > API**
- **Segment IDs not showing?** They appear after creation; go back to Segments list and click each one to view the ID
- **Multiple options for auth?** Use API Key (not OAuth) — simpler to integrate

---

**Once you complete these steps and share the credentials, I'll connect your website form to Beehiiv and set up automatic segmentation.**

Questions while setting up? Just reply with where you got stuck.
