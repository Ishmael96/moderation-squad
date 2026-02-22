# ═══════════════════════════════════════════════════════════════
#  MODERATION SQUAD — Render Deployment Version
#  Persistent SQLite DB | No Colab | Fixed URL forever
# ═══════════════════════════════════════════════════════════════
import sqlite3, json, threading, random, os
from datetime import datetime
from flask import Flask, request, session, redirect, jsonify
import requests as req

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "modsquad_2025_key_secure")

BREVO_KEY    = "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"
SENDER_EMAIL = "australiapaper33@gmail.com"
SENDER_NAME  = "Moderation Squad"
S_EMAIL      = "support@moderationsquad.com"
S_PHONE      = "+1 (888) 266-3763"

WHITELIST = ["australiapaper33@gmail.com","wizardacademic@gmail.com","celestinerotich969@gmail.com"]

# ── DATABASE ──────────────────────────────────────────────────
DB_PATH = os.environ.get("DB_PATH", "modsquad.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT,
            level TEXT DEFAULT 'Newcomer',
            jobs_done INTEGER DEFAULT 0,
            earned REAL DEFAULT 0.0,
            member_since TEXT,
            avatar TEXT,
            verifications TEXT DEFAULT '{}',
            applied_jobs TEXT DEFAULT '[]',
            schedule TEXT DEFAULT '{}',
            completed_courses TEXT DEFAULT '[]'
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            msg TEXT,
            time TEXT
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS otps (
            email TEXT PRIMARY KEY,
            code TEXT,
            created_at TEXT
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            role TEXT,
            msg TEXT,
            time TEXT
        )""")
        db.commit()

init_db()

# ── DB HELPERS ────────────────────────────────────────────────
def get_user(email):
    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if row:
            u = dict(row)
            u["verifications"] = json.loads(u["verifications"] or "{}")
            u["applied_jobs"]  = json.loads(u["applied_jobs"] or "[]")
            u["schedule"]      = json.loads(u["schedule"] or "{}")
            u["completed_courses"] = json.loads(u["completed_courses"] or "[]")
            return u
        return {}

def save_user(u):
    with get_db() as db:
        db.execute("""INSERT INTO users (email,name,level,jobs_done,earned,member_since,avatar,verifications,applied_jobs,schedule,completed_courses)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(email) DO UPDATE SET
            name=excluded.name, level=excluded.level, jobs_done=excluded.jobs_done,
            earned=excluded.earned, member_since=excluded.member_since, avatar=excluded.avatar,
            verifications=excluded.verifications, applied_jobs=excluded.applied_jobs,
            schedule=excluded.schedule, completed_courses=excluded.completed_courses""",
            (u["email"], u.get("name",""), u.get("level","Newcomer"), u.get("jobs_done",0),
             u.get("earned",0.0), u.get("member_since",""), u.get("avatar"),
             json.dumps(u.get("verifications",{})), json.dumps(u.get("applied_jobs",[])),
             json.dumps(u.get("schedule",{})), json.dumps(u.get("completed_courses",[]))))
        db.commit()

def add_notif(email, msg):
    with get_db() as db:
        db.execute("INSERT INTO notifications (email,msg,time) VALUES (?,?,?)",
            (email, msg, datetime.now().strftime("%b %d, %I:%M %p")))
        # Keep only last 20
        db.execute("""DELETE FROM notifications WHERE id NOT IN (
            SELECT id FROM notifications WHERE email=? ORDER BY id DESC LIMIT 20)
            AND email=?""", (email, email))
        db.commit()

def get_notifs(email):
    with get_db() as db:
        rows = db.execute("SELECT msg,time FROM notifications WHERE email=? ORDER BY id DESC", (email,)).fetchall()
        return [dict(r) for r in rows]

def get_chats(email):
    with get_db() as db:
        rows = db.execute("SELECT role,msg,time FROM chats WHERE email=? ORDER BY id", (email,)).fetchall()
        return [dict(r) for r in rows]

def add_chat(email, role, msg):
    t = datetime.now().strftime("%I:%M %p")
    with get_db() as db:
        db.execute("INSERT INTO chats (email,role,msg,time) VALUES (?,?,?,?)", (email, role, msg, t))
        db.commit()
    return t

def set_otp(email, code):
    with get_db() as db:
        db.execute("INSERT INTO otps (email,code,created_at) VALUES (?,?,?) ON CONFLICT(email) DO UPDATE SET code=excluded.code,created_at=excluded.created_at",
            (email, code, datetime.now().isoformat()))
        db.commit()

def check_otp(email, code):
    with get_db() as db:
        row = db.execute("SELECT code FROM otps WHERE email=?", (email,)).fetchone()
        if row and row["code"] == code:
            db.execute("DELETE FROM otps WHERE email=?", (email,))
            db.commit()
            return True
        return False

# ── EMAIL ─────────────────────────────────────────────────────
def brevo(to, subject, html):
    try:
        req.post("https://api.brevo.com/v3/smtp/email",
            json={"sender":{"name":SENDER_NAME,"email":SENDER_EMAIL},"to":[{"email":to}],"subject":subject,"htmlContent":html},
            headers={"accept":"application/json","api-key":BREVO_KEY,"content-type":"application/json"},timeout=10)
    except: pass

def send_otp(email, otp):
    brevo(email,"Moderation Squad — Secure Login Code",f"""
<div style="font-family:Arial,sans-serif;background:#f5f5f5;padding:40px 0;">
<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">
<div style="background:#C8332A;padding:32px;text-align:center;">
<p style="color:#fff;font-size:20px;font-weight:900;letter-spacing:4px;margin:0;">MODERATION SQUAD</p>
<p style="color:rgba(255,255,255,0.75);font-size:11px;letter-spacing:3px;margin:8px 0 0;">SECURE LOGIN CODE</p></div>
<div style="padding:40px;">
<p style="font-size:15px;color:#1a0a0a;font-weight:600;">Dear Moderator,</p>
<p style="font-size:14px;color:#555;line-height:1.8;">Your one-time secure login code is below. Valid for <strong>10 minutes</strong>.</p>
<div style="text-align:center;margin:32px 0;"><div style="display:inline-block;border:2px dashed #C8332A;border-radius:14px;padding:24px 56px;">
<p style="font-size:10px;color:#999;letter-spacing:3px;margin:0 0 10px;">YOUR CODE</p>
<p style="font-size:48px;font-weight:900;color:#C8332A;letter-spacing:12px;margin:0;">{otp}</p></div></div>
<p style="font-size:12px;color:#888;text-align:center;">⏱ Expires in 10 minutes &nbsp;·&nbsp; 🔒 Never share this code</p></div>
<div style="background:#1a0a0a;padding:18px;text-align:center;">
<p style="color:rgba(255,255,255,0.5);font-size:11px;margin:0;">© 2025 Moderation Squad · {S_EMAIL}</p></div></div></div>""")

def send_app_email(email, name, title, company, pay, days):
    brevo(email,f"Application Received — {title} at {company}",f"""
<div style="font-family:Arial,sans-serif;background:#f5f5f5;padding:40px 0;">
<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">
<div style="background:#C8332A;padding:32px;text-align:center;">
<p style="color:#fff;font-size:20px;font-weight:900;letter-spacing:4px;margin:0;">MODERATION SQUAD</p>
<p style="color:rgba(255,255,255,0.75);font-size:11px;letter-spacing:3px;margin:8px 0 0;">APPLICATION CONFIRMATION</p></div>
<div style="padding:40px;">
<p style="font-size:15px;color:#1a0a0a;font-weight:600;">Dear {name},</p>
<p style="font-size:14px;color:#555;line-height:1.8;">Your application has been received! We will respond within <strong>{days} business day{'s' if days>1 else ''}</strong>.</p>
<div style="background:#fff8f8;border-left:4px solid #C8332A;border-radius:8px;padding:18px 22px;margin:24px 0;">
<p style="font-size:11px;color:#999;letter-spacing:1px;text-transform:uppercase;margin:0 0 8px;">Application Details</p>
<p style="font-size:17px;font-weight:700;color:#1a0a0a;margin:0 0 5px;">💼 {title}</p>
<p style="font-size:13px;color:#555;margin:0 0 5px;">🏢 {company}</p>
<p style="font-size:14px;color:#C8332A;font-weight:700;margin:0;">💵 {pay}</p></div>
<p style="font-size:13px;color:#555;line-height:1.8;">While waiting, ensure your profile is fully verified — verified moderators get hired <strong>3x faster</strong>.</p></div>
<div style="background:#1a0a0a;padding:18px;text-align:center;">
<p style="color:rgba(255,255,255,0.5);font-size:11px;margin:0;">© 2025 Moderation Squad · {S_EMAIL} · {S_PHONE}</p></div></div></div>""")

# ── STATIC DATA ───────────────────────────────────────────────
SOCIAL=[
    ("https://www.facebook.com/ModSquad/","Facebook","M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"),
    ("https://twitter.com/ModSquad","X / Twitter","M23 3a10.9 10.9 0 0 1-3.14 1.53A4.48 4.48 0 0 0 22.43.36a9 9 0 0 1-2.88 1.1A4.52 4.52 0 0 0 16.11 0c-2.5 0-4.52 2.02-4.52 4.52 0 .35.04.7.11 1.03C7.69 5.4 4.07 3.58 1.64.9a4.52 4.52 0 0 0-.61 2.27c0 1.57.8 2.95 2.01 3.76a4.5 4.5 0 0 1-2.05-.57v.06c0 2.19 1.56 4.02 3.63 4.43a4.5 4.5 0 0 1-2.04.08 4.52 4.52 0 0 0 4.22 3.14A9.06 9.06 0 0 1 0 19.54a12.77 12.77 0 0 0 6.92 2.03c8.3 0 12.84-6.88 12.84-12.85 0-.2 0-.39-.01-.58A9.17 9.17 0 0 0 23 3z"),
    ("https://www.instagram.com/modsquadinc/","Instagram","M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37zm1.5-4.87h.01M6.5 6.5h11a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-11a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2z"),
    ("https://www.linkedin.com/company/modsquad","LinkedIn","M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6zM2 9h4v12H2z M4 6a2 2 0 1 0 0-4 2 2 0 0 0 0 4z"),
    ("https://www.youtube.com/@ModSquadInc","YouTube","M22.54 6.42a2.78 2.78 0 0 0-1.95-1.96C18.88 4 12 4 12 4s-6.88 0-8.59.46A2.78 2.78 0 0 0 1.46 6.42 29 29 0 0 0 1 12a29 29 0 0 0 .46 5.58 2.78 2.78 0 0 0 1.95 1.96C5.12 20 12 20 12 20s6.88 0 8.59-.46a2.78 2.78 0 0 0 1.96-1.96A29 29 0 0 0 23 12a29 29 0 0 0-.46-5.58zM9.75 15.02V8.98L15.5 12l-5.75 3.02z"),
]

ALL_JOBS=[
 {"pg":1,"icon":"💬","title":"Basic Chat Monitor","company":"RetailBrand Co.","pay":"$5/hr","hrs":"10 hrs/wk","desc":"Monitor customer chat queues and flag inappropriate content. No experience required. Perfect first role.","locked":False},
 {"pg":1,"icon":"📧","title":"Email Response Support","company":"SmallBiz Store","pay":"$5/hr","hrs":"8 hrs/wk","desc":"Respond to customer emails using provided templates. Fully flexible schedule, work anytime you like.","locked":False},
 {"pg":1,"icon":"🛡️","title":"Forum Comment Moderator","company":"CommunityHub","pay":"$6/hr","hrs":"12 hrs/wk","desc":"Review forum posts and comments, remove policy violations. Great introduction to moderation work.","locked":False},
 {"pg":1,"icon":"🎯","title":"Standard Chat Moderator","company":"TechCorp Inc.","pay":"$12/hr","hrs":"25 hrs/wk","desc":"Full-time chat moderation for a leading tech platform with millions of daily users.","locked":True,"req":"🟢 Junior (6+ jobs)"},
 {"pg":1,"icon":"📝","title":"Content Reviewer","company":"MediaFlow","pay":"$11/hr","hrs":"20 hrs/wk","desc":"Review user-generated content for policy compliance across a major media platform.","locked":True,"req":"🟢 Junior (6+ jobs)"},
 {"pg":2,"icon":"📱","title":"Social Media Moderator","company":"BrandBoost","pay":"$14/hr","hrs":"30 hrs/wk","desc":"Moderate comments and posts across Facebook, Instagram, and Twitter for major brands.","locked":True,"req":"🟡 Senior (21+ jobs)"},
 {"pg":2,"icon":"🎮","title":"Gaming Community Mod","company":"GameStream Pro","pay":"$16/hr","hrs":"35 hrs/wk","desc":"Moderate live gaming streams and community Discord servers for a top gaming platform.","locked":True,"req":"🟡 Senior (21+ jobs)"},
 {"pg":2,"icon":"🌐","title":"Multilingual Content Mod","company":"GlobalReach","pay":"$15/hr","hrs":"30 hrs/wk","desc":"Moderate content in English and Spanish across global e-commerce and social platforms.","locked":True,"req":"🟡 Senior (21+ jobs)"},
 {"pg":2,"icon":"🔍","title":"Trust & Safety Analyst","company":"SafeNet Inc.","pay":"$17/hr","hrs":"35 hrs/wk","desc":"Investigate abuse reports, perform account reviews, and escalate complex violation cases.","locked":True,"req":"🟡 Senior (21+ jobs)"},
 {"pg":2,"icon":"📊","title":"Metrics & QA Reviewer","company":"DataMod LLC","pay":"$14/hr","hrs":"25 hrs/wk","desc":"Review moderation quality scores and compile weekly performance and compliance reports.","locked":True,"req":"🟡 Senior (21+ jobs)"},
 {"pg":3,"icon":"🏆","title":"Senior Moderator","company":"MegaCorp Media","pay":"$18/hr","hrs":"40 hrs/wk","desc":"Lead moderation shifts, mentor junior team members, and maintain quality standards.","locked":True,"req":"🔴 Elite (50+ jobs)"},
 {"pg":3,"icon":"👑","title":"Lead Moderator","company":"Enterprise Plus","pay":"$20/hr","hrs":"40 hrs/wk","desc":"Oversee a team of 10+ moderators across multiple client accounts and time zones.","locked":True,"req":"🔴 Elite (50+ jobs)"},
 {"pg":3,"icon":"🔐","title":"Trust & Safety Specialist","company":"SafeNet Inc.","pay":"$22/hr","hrs":"40 hrs/wk","desc":"Senior-level T&S work including policy development and cross-team collaboration.","locked":True,"req":"🔴 Elite (50+ jobs)"},
 {"pg":3,"icon":"📺","title":"Streaming Platform Mod","company":"LiveFeed TV","pay":"$19/hr","hrs":"40 hrs/wk","desc":"Real-time moderation of major live streaming events and viewer chat management.","locked":True,"req":"🔴 Elite (50+ jobs)"},
 {"pg":3,"icon":"💼","title":"Client Account Manager","company":"ModSquad HQ","pay":"$21/hr","hrs":"40 hrs/wk","desc":"Manage client relationships, SLA compliance, and moderation team performance metrics.","locked":True,"req":"🔴 Elite (50+ jobs)"},
 {"pg":4,"icon":"🤖","title":"AI Content Reviewer","company":"TechAI Labs","pay":"$20/hr","hrs":"40 hrs/wk","desc":"Review AI-generated content for safety, quality, and policy compliance at scale.","locked":True,"req":"🔴 Elite (50+ jobs)"},
 {"pg":4,"icon":"🌍","title":"Global Mod Team Lead","company":"WorldMod Co.","pay":"$22/hr","hrs":"40 hrs/wk","desc":"Lead a global team of 20+ moderators operating across 5 continents and time zones.","locked":True,"req":"🔴 Elite (50+ jobs)"},
 {"pg":4,"icon":"🎬","title":"Entertainment Mod Spec","company":"StudioX","pay":"$19/hr","hrs":"40 hrs/wk","desc":"Moderate fan communities for major entertainment brands, film studios, and award shows.","locked":True,"req":"🔴 Elite (50+ jobs)"},
 {"pg":4,"icon":"🏥","title":"Healthcare Comm Mod","company":"MedConnect","pay":"$20/hr","hrs":"35 hrs/wk","desc":"Moderate sensitive healthcare community discussions with empathy and compliance focus.","locked":True,"req":"🔴 Elite (50+ jobs)"},
 {"pg":4,"icon":"🎓","title":"EdTech Moderator","company":"LearnWorld","pay":"$18/hr","hrs":"30 hrs/wk","desc":"Moderate online learning platforms, student discussion forums, and virtual classrooms.","locked":True,"req":"🔴 Elite (50+ jobs)"},
]

COURSES=[
 {"id":0,"icon":"🛡️","title":"Chat Moderation Fundamentals","level":"Beginner","dur":"4 hrs","desc":"Learn the basics of professional chat moderation, community guidelines, and escalation procedures.","locked":False,
  "lessons":[
   ("What Is Chat Moderation?","Chat moderation is the practice of monitoring and managing online conversations to ensure they remain safe, respectful, and on-topic.\n\nAs a moderator, you are the first line of defense against harmful content. Your work directly impacts thousands of users every day.\n\n📌 KEY RESPONSIBILITIES:\n• Monitor live chat streams in real-time\n• Identify and remove policy-violating content\n• Issue warnings and bans to rule-breaking users\n• Escalate serious issues to senior staff immediately\n• Keep accurate records of all moderation actions\n\n💡 WHY IT MATTERS:\nResearch shows that 70% of users leave a platform permanently after experiencing harassment. Your role protects the community and keeps users engaged.\n\n✅ After this lesson you should understand the core purpose of chat moderation and why it matters for online platforms."),
   ("Community Guidelines","Every platform has its own community guidelines, but they share common themes.\n\n✅ GENERALLY ALLOWED:\n• Constructive criticism and respectful debate\n• Sharing personal experiences and opinions\n• Asking questions and seeking help\n• Creative content within platform theme\n\n❌ NOT ALLOWED:\n• Hate speech or discrimination\n• Harassment, bullying, or targeted attacks\n• Spam, self-promotion, or repetitive posting\n• Graphic violence or disturbing imagery\n• Doxxing — sharing private personal information\n• Threats of violence, real or implied\n\n📌 KEY PRINCIPLE — CONSISTENCY:\nApply rules the same way to every user, regardless of their status, popularity, or how long they have been on the platform.\n\n💡 PRO TIP: When unsure whether content violates guidelines, ask: 'Would this make another user feel unsafe or unwelcome?' If yes, it likely warrants action."),
   ("Handling Difficult Users","Not every user you deal with will be cooperative. Here are proven strategies:\n\n😤 TYPES OF DIFFICULT USERS:\n• The Arguer — disputes every moderation action\n• The Rule-Pusher — constantly tests boundaries\n• The Evader — creates new accounts to avoid bans\n• The Harasser — targets specific users or moderators\n• The Spammer — floods chat with repetitive content\n\n🛠️ PROVEN STRATEGIES:\n1. STAY CALM — Never respond emotionally. All actions must be professional.\n2. WARN FIRST — Give a clear, specific warning before taking action.\n3. DOCUMENT — Screenshot and log all incidents with timestamps.\n4. BE CONSISTENT — Apply rules the same way every time.\n5. ESCALATE — Know exactly when and how to escalate.\n6. SELF-CARE — Moderation can be mentally taxing. Use support resources.\n\n📝 SAMPLE WARNING MESSAGE:\n'Hi [username] — your recent message was removed for violating our community guidelines on [specific rule]. This is your first warning. A second violation will result in a temporary suspension.'\n\n⚠️ REMEMBER: You enforce platform rules, not your personal opinions."),
   ("Escalation Procedures","Knowing when and how to escalate is one of the most critical moderation skills.\n\n🚨 ALWAYS ESCALATE IMMEDIATELY FOR:\n• Any threats of violence or self-harm\n• Illegal content (CSAM, terrorism, fraud)\n• Coordinated harassment campaigns\n• Potential account hacking or identity theft\n• Viral or media-coverage incidents\n• Any situation where you feel uncertain\n\n📋 HOW TO ESCALATE PROPERLY:\n1. DO NOT delete the content before escalating — it is evidence\n2. Screenshot the content with timestamps visible\n3. Note the username, user ID, and post URL\n4. Use the designated escalation channel immediately\n5. Write a clear, factual summary — no personal opinions\n6. Follow up if no response within 1 hour\n\n💡 GOLDEN RULE: When in doubt, escalate. It is always better to escalate unnecessarily than to miss a serious incident."),
   ("Quiz & Certification 🎓","FINAL ASSESSMENT — Chat Moderation Fundamentals\n\n❓ Q1: What should you do FIRST when encountering a rule violation?\nA) Ban the user immediately\nB) Issue a clear, specific warning ✅ CORRECT\nC) Ignore it if it seems minor\nD) Ask other users what they think\n\n❓ Q2: When should you escalate an issue?\nA) Only for the most extreme content\nB) Whenever you feel uncertain ✅ CORRECT\nC) Never — handle everything yourself\nD) Only when your manager is online\n\n❓ Q3: What is doxxing?\nA) Sharing funny memes in chat\nB) Posting too many messages quickly\nC) Sharing someone's private personal information ✅ CORRECT\nD) Using multiple accounts\n\n❓ Q4: Why must you NOT delete content before escalating?\nA) It takes too much time\nB) The content may be needed as evidence ✅ CORRECT\nC) Deletion is against company policy\nD) Users might notice\n\n🎉 CONGRATULATIONS!\nYou have successfully completed Chat Moderation Fundamentals!\n\n🏆 Certificate: Chat Moderation Fundamentals — Beginner\n📅 Issued: {}\n\nThis certificate has been recorded on your profile. Complete more courses to unlock advanced positions!".format(datetime.now().strftime('%B %d, %Y')))
  ]},
 {"id":1,"icon":"📋","title":"Content Policy & Guidelines","level":"Beginner","dur":"2 hrs","desc":"Understand content policies, what to flag, and how to handle edge cases professionally.","locked":False,
  "lessons":[
   ("Types of Violating Content","Content violations are organized by severity. Knowing the difference helps you act with the right level of urgency.\n\n🔴 CRITICAL — Remove immediately AND escalate now:\n• Child sexual abuse material (CSAM) — Zero tolerance\n• Credible threats of violence against real people\n• Terrorism recruitment or glorification\n• Detailed instructions for mass violence\n\n🟡 HIGH — Remove AND issue final warning:\n• Targeted hate speech against protected groups\n• Graphic violence without clear news or artistic context\n• Sustained harassment campaigns\n• Explicit sexual content in non-designated spaces\n\n🟢 MEDIUM — Warn user, may remove:\n• Mild profanity or offensive language\n• Off-topic spam or repetitive posts\n• Minor self-promotion outside designated areas\n\n💡 When severity is unclear: Always choose to escalate rather than under-react."),
   ("Edge Cases & Grey Areas","Not everything is black and white. Here's how to handle the most common grey areas:\n\n🎭 SATIRE & PARODY:\nGenuine satire can criticize without violating. Ask:\n• Is satirical intent clear to a reasonable reader?\n• Does it punch down at vulnerable groups?\n• Could it be mistaken for a real threat?\n\n📰 NEWS & DOCUMENTARY CONTENT:\nGraphic content may have legitimate newsworthiness:\n• Is this from a credible journalistic source?\n• Is the graphic element necessary to the story?\n• Has the platform approved news content exceptions?\n\n🌍 CULTURAL CONTEXT:\n• Slang acceptable in one community may be offensive in another\n• Religious references require cultural sensitivity\n• When uncertain, consult your escalation contact\n\n✅ DECISION FRAMEWORK:\n1. Who could be harmed by this content?\n2. What is the most likely intent?\n3. What would a reasonable person think?\n4. When in doubt — escalate."),
   ("Quiz & Certificate 🎓","ASSESSMENT — Content Policy & Guidelines\n\n❓ Q1: A user posts graphic war footage with a news article link. You should:\nA) Delete it immediately\nB) Evaluate newsworthiness and escalate if unsure ✅ CORRECT\nC) Ignore it completely\nD) Ban the user immediately\n\n❓ Q2: A post uses slang that seems offensive. You should:\nA) Always delete it immediately\nB) Consider cultural context and platform norms ✅ CORRECT\nC) Ask users if they found it offensive\nD) Ignore it — slang is never a violation\n\n❓ Q3: What severity level is CSAM content?\nA) Medium\nB) High\nC) Critical — remove and escalate immediately ✅ CORRECT\nD) Low\n\n🎉 CERTIFICATE EARNED!\nContent Policy & Guidelines — Beginner\n📅 {}\n\nYour certification has been recorded on your profile!".format(datetime.now().strftime('%B %d, %Y')))
  ]},
 {"id":2,"icon":"💬","title":"Effective Communication","level":"Beginner","dur":"3 hrs","desc":"Master professional tone, empathy, and de-escalation techniques for difficult interactions.","locked":False,
  "lessons":[
   ("Professional Tone","Every message you send as a moderator represents the platform. Always be:\n\n✅ CLEAR — Be specific about what rule was broken:\n❌ Bad: 'Your post was removed.'\n✅ Good: 'Your post was removed because it contained personal information about another user, violating Section 4.2 of our Community Guidelines.'\n\n✅ NEUTRAL — Show no personal bias:\n❌ Bad: 'I personally find your opinion offensive.'\n✅ Good: 'This content does not meet our community standards for respectful discourse.'\n\n✅ FIRM — Be clear about consequences:\n❌ Bad: 'Maybe try not to do that again?'\n✅ Good: 'This is your first warning. A second violation will result in a 24-hour suspension.'\n\n✅ EMPATHETIC — Acknowledge the user's perspective:\n❌ Bad: 'You broke the rules, end of story.'\n✅ Good: 'I understand this may feel frustrating. Our guidelines apply equally to all users to keep our community safe.'\n\n📝 PERFECT MESSAGE FORMULA:\n1. Acknowledge (briefly)\n2. State the action taken\n3. Cite the specific rule\n4. State consequences for further violations\n5. Keep it under 100 words"),
   ("De-escalation","When a user is angry about a moderation action, your goal is to de-escalate without backing down.\n\n🔥 THE 5-STEP METHOD:\n\nStep 1 — ACKNOWLEDGE frustration:\n'I understand you are frustrated by this decision.'\n\nStep 2 — VALIDATE without agreeing:\n'I can see why this situation feels unfair from your perspective.'\n\nStep 3 — EXPLAIN the rule calmly:\n'Our community guidelines require [specific rule] to protect all members.'\n\nStep 4 — OFFER a path forward:\n'If you believe this was an error, you can submit an appeal through [link].'\n\nStep 5 — SET A LIMIT:\n'I am happy to help, but I will need to end this conversation if it continues to be disrespectful.'\n\n🚫 NEVER:\n• Match their emotional energy\n• Use sarcasm or passive-aggression\n• Make it personal\n• Back down from a correct moderation decision\n• Engage with insults directed at you"),
   ("Quiz & Certificate 🎓","ASSESSMENT — Effective Communication\n\n❓ Q1: A user angrily messages after their post was removed. You should:\nA) Ignore them\nB) Apologize and restore the post\nC) Acknowledge frustration, explain the rule, offer appeal process ✅ CORRECT\nD) Immediately ban them\n\n❓ Q2: A good moderation message always includes:\nA) Your personal opinion on the content\nB) The specific rule violated and consequences ✅ CORRECT\nC) A lengthy explanation of all guidelines\nD) An apology\n\n❓ Q3: The Grey Rock Method means:\nA) Banning rude users immediately\nB) Becoming neutral, giving minimal responses to abusive users ✅ CORRECT\nC) Ignoring all messages from difficult users\nD) Escalating every hostile interaction\n\n🎉 CERTIFICATE EARNED!\nEffective Communication — Beginner\n📅 {}\n\nExcellent work! You have completed all available beginner courses. Intermediate courses unlock at Junior level.".format(datetime.now().strftime('%B %d, %Y')))
  ]},
 {"id":3,"icon":"🔒","title":"Trust & Safety Basics","level":"Intermediate","dur":"5 hrs","desc":"Introduction to trust and safety operations, abuse detection, and professional reporting.","locked":True,"lessons":[]},
 {"id":4,"icon":"📊","title":"Data & Reporting","level":"Intermediate","dur":"3 hrs","desc":"Learn to track moderation metrics and write professional incident reports.","locked":True,"lessons":[]},
 {"id":5,"icon":"🏆","title":"Advanced Moderation Techniques","level":"Senior","dur":"6 hrs","desc":"Advanced strategies for high-volume platforms and complex moderation scenarios.","locked":True,"lessons":[]},
]

# ── CSS ───────────────────────────────────────────────────────
CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap');
:root{
  --bg:#f4f6f9;--panel:#ffffff;--card:#ffffff;--sb:#ffffff;
  --red:#C8332A;--red2:#a01f18;--red-light:#fff0ef;--red-mid:#fde0de;
  --text:#1a0a0a;--muted:#6b7280;--bdr:#e5e7eb;--bdr2:#f3f4f6;
  --ok:#16a34a;--ok-bg:#f0fdf4;--ok-bdr:#bbf7d0;
  --warn:#d97706;--warn-bg:#fffbeb;--warn-bdr:#fde68a;
  --bad:#dc2626;--pur:#7c3aed;--pur-bg:#f5f3ff;
  --shadow:0 1px 3px rgba(0,0,0,0.08),0 1px 2px rgba(0,0,0,0.05);
  --shadow-md:0 4px 16px rgba(0,0,0,0.08);
  --shadow-lg:0 10px 32px rgba(0,0,0,0.1);
}
*{margin:0;padding:0;box-sizing:border-box;}
body{background:var(--bg);color:var(--text);font-family:'Plus Jakarta Sans',sans-serif;min-height:100vh;}
a{text-decoration:none;color:inherit;}
::-webkit-scrollbar{width:5px;}::-webkit-scrollbar-track{background:var(--bg);}
::-webkit-scrollbar-thumb{background:var(--bdr);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:#C8332A;}
.layout{display:flex;min-height:100vh;}
.sb{width:240px;background:var(--sb);border-right:1px solid var(--bdr);display:flex;flex-direction:column;position:fixed;height:100vh;z-index:50;overflow-y:auto;box-shadow:var(--shadow);}
.sb-logo{padding:20px;border-bottom:1px solid var(--bdr);background:var(--red);}
.sb-logo h2{font-size:11px;font-weight:900;letter-spacing:3px;color:#fff;}
.sb-logo p{font-size:9px;color:rgba(255,255,255,0.7);letter-spacing:2px;margin-top:2px;}
.nb-sec{padding:14px 16px 5px;font-size:9px;letter-spacing:2px;color:var(--muted);text-transform:uppercase;font-weight:700;}
.ni{display:flex;align-items:center;gap:11px;padding:10px 16px;color:var(--muted);font-size:13px;font-weight:500;transition:all 0.18s;border-left:3px solid transparent;margin:1px 0;}
.ni:hover{color:var(--red);background:var(--red-light);border-left-color:var(--red);}
.ni.active{color:var(--red);background:var(--red-light);border-left-color:var(--red);font-weight:600;}
.ni svg{width:16px;height:16px;flex-shrink:0;}
.nbadge{margin-left:auto;background:var(--red);color:#fff;font-size:9px;font-weight:700;padding:2px 7px;border-radius:999px;}
.sb-bottom{margin-top:auto;border-top:1px solid var(--bdr);}
.sb-sup{background:var(--red-light);border:1px solid var(--red-mid);border-radius:10px;padding:12px;margin:10px;font-size:11px;color:var(--muted);line-height:1.8;}
.sb-sup a{color:var(--red);font-weight:600;}
.sb-sup strong{color:var(--text);}
.sb-logout{display:flex;align-items:center;gap:11px;padding:12px 16px;color:var(--bad);font-size:13px;font-weight:600;transition:all 0.18s;border-left:3px solid transparent;cursor:pointer;margin:4px 0 12px;}
.sb-logout:hover{background:#fef2f2;border-left-color:var(--bad);}
.sb-logout svg{width:16px;height:16px;}
.mc{margin-left:240px;flex:1;padding:24px 28px;min-height:100vh;}
.topbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;flex-wrap:wrap;gap:12px;}
.topbar h1{font-size:20px;font-weight:800;letter-spacing:-0.5px;color:var(--text);}
.topbar p{font-size:12px;color:var(--muted);margin-top:3px;}
.tr{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.bdg{display:inline-flex;align-items:center;gap:5px;padding:4px 11px;border-radius:999px;font-size:10px;font-weight:700;}
.b-red{background:var(--red-light);color:var(--red);border:1px solid var(--red-mid);}
.b-green{background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-bdr);}
.b-warn{background:var(--warn-bg);color:var(--warn);border:1px solid var(--warn-bdr);}
.b-pur{background:var(--pur-bg);color:var(--pur);border:1px solid #ddd6fe;}
.b-blue{background:#eff6ff;color:#2563eb;border:1px solid #bfdbfe;}
.b-grey{background:var(--bdr2);color:var(--muted);border:1px solid var(--bdr);}
.card{background:var(--card);border:1px solid var(--bdr);border-radius:14px;padding:20px;box-shadow:var(--shadow);}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.g3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;}
.sc{background:var(--card);border:1px solid var(--bdr);border-radius:14px;padding:18px;position:relative;overflow:hidden;box-shadow:var(--shadow);}
.sc::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;}
.c1::before{background:var(--red);}
.c2::before{background:var(--ok);}
.c3::before{background:var(--pur);}
.c4::before{background:var(--warn);}
.sl{font-size:10px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;font-weight:600;}
.sv{font-size:26px;font-weight:800;letter-spacing:-1px;margin-bottom:4px;}
.ss2{font-size:11px;color:var(--muted);}
.si2{position:absolute;top:14px;right:14px;font-size:22px;opacity:0.12;}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;padding:9px 18px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;border:none;transition:all 0.18s;font-family:'Plus Jakarta Sans',sans-serif;white-space:nowrap;}
.bp{background:var(--red);color:#fff;}
.bp:hover{background:var(--red2);transform:translateY(-1px);box-shadow:0 6px 18px rgba(200,51,42,0.3);}
.bo{background:#fff;color:var(--text);border:1px solid var(--bdr);}
.bo:hover{border-color:var(--red);color:var(--red);}
.bs{background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-bdr);}
.bl{background:var(--bdr2);color:var(--muted);cursor:not-allowed;border:1px solid var(--bdr);opacity:0.6;}
.bsm{padding:7px 14px;font-size:12px;}
.jc{background:var(--card);border:1px solid var(--bdr);border-radius:13px;padding:18px;transition:all 0.2s;display:flex;flex-direction:column;box-shadow:var(--shadow);}
.jc:not(.lk):hover{border-color:var(--red);transform:translateY(-2px);box-shadow:var(--shadow-md);}
.jc.lk{opacity:0.45;pointer-events:none;}
.jt{font-size:14px;font-weight:700;margin-bottom:3px;line-height:1.3;color:var(--text);}
.jco{font-size:11px;color:var(--muted);margin-bottom:9px;}
.jd{font-size:12px;color:var(--muted);line-height:1.7;margin-bottom:10px;flex:1;}
.jm{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:12px;}
.tg{font-size:10px;padding:3px 8px;border-radius:5px;font-weight:600;}
.tp{background:var(--ok-bg);color:var(--ok);}
.tt{background:#eff6ff;color:#2563eb;}
.tl{background:var(--pur-bg);color:var(--pur);}
.tn{background:var(--red-light);color:var(--red);}
.pb{width:100%;height:7px;background:var(--bdr);border-radius:999px;overflow:hidden;}
.pf{height:100%;border-radius:999px;background:var(--red);transition:width 1.2s ease;}
.vi{display:flex;align-items:center;justify-content:space-between;padding:13px 14px;background:var(--bg);border-radius:10px;margin-bottom:7px;border:1px solid var(--bdr);}
.vl{display:flex;align-items:center;gap:11px;}
.vic{width:36px;height:36px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;}
.vd-bg{background:var(--ok-bg);border:1px solid var(--ok-bdr);}
.vw-bg{background:var(--warn-bg);border:1px solid var(--warn-bdr);}
.vn{font-size:13px;font-weight:600;color:var(--text);}
.vs2{font-size:11px;color:var(--muted);margin-top:2px;}
.vst{font-size:11px;font-weight:700;padding:3px 11px;border-radius:999px;}
.vst-ok{background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-bdr);}
.vst-warn{background:var(--warn-bg);color:var(--warn);border:1px solid var(--warn-bdr);}
.avw{position:relative;width:82px;height:82px;flex-shrink:0;}
.av{width:82px;height:82px;border-radius:50%;background:linear-gradient(135deg,var(--red),var(--red2));display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:800;color:#fff;overflow:hidden;border:3px solid var(--red-mid);}
.av img{width:100%;height:100%;object-fit:cover;}
.ave{position:absolute;bottom:0;right:0;width:26px;height:26px;background:var(--red);border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;border:2px solid #fff;font-size:12px;box-shadow:0 2px 6px rgba(0,0,0,0.15);}
.form-group{margin-bottom:16px;}
.form-label{font-size:11px;color:var(--muted);font-weight:600;margin-bottom:6px;display:block;letter-spacing:0.5px;text-transform:uppercase;}
.form-input{width:100%;background:#fff;border:1px solid var(--bdr);border-radius:8px;padding:10px 13px;font-size:13px;color:var(--text);font-family:'Plus Jakarta Sans',sans-serif;transition:all 0.18s;outline:none;}
.form-input:focus{border-color:var(--red);box-shadow:0 0 0 3px rgba(200,51,42,0.08);}
.toast{position:fixed;bottom:22px;right:22px;padding:12px 20px;border-radius:10px;font-size:13px;font-weight:600;opacity:0;transform:translateY(10px);transition:all 0.3s;z-index:9999;pointer-events:none;max-width:320px;line-height:1.5;box-shadow:var(--shadow-lg);}
.toast.show{opacity:1;transform:translateY(0);}
.ts{background:#16a34a;color:#fff;}.te{background:#dc2626;color:#fff;}.ti{background:var(--red);color:#fff;}
.sh{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;}
.sh h2{font-size:14px;font-weight:700;color:var(--text);}
.nbell{position:relative;cursor:pointer;padding:8px;border-radius:9px;border:1px solid var(--bdr);background:#fff;transition:all 0.18s;box-shadow:var(--shadow);}
.nbell:hover{border-color:var(--red);}
.ndot{position:absolute;top:5px;right:5px;width:8px;height:8px;background:var(--red);border-radius:50%;border:2px solid #fff;}
.ndrop{position:absolute;top:44px;right:0;width:300px;background:#fff;border:1px solid var(--bdr);border-radius:14px;z-index:300;display:none;box-shadow:var(--shadow-lg);}
.ndrop.open{display:block;}
.chat-wrap{display:flex;flex-direction:column;height:450px;background:#fff;border-radius:12px;border:1px solid var(--bdr);overflow:hidden;box-shadow:var(--shadow);}
.chat-msgs{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;background:var(--bg);}
.cmsg{max-width:78%;padding:11px 14px;border-radius:12px;font-size:13px;line-height:1.6;}
.cmsg.sup{background:#fff;border:1px solid var(--bdr);align-self:flex-start;border-radius:4px 14px 14px 14px;box-shadow:var(--shadow);}
.cmsg.usr{background:var(--red);color:#fff;align-self:flex-end;border-radius:14px 4px 14px 14px;}
.cmsg.usr .mt{color:rgba(255,255,255,0.7);}
.mt{font-size:10px;color:var(--muted);margin-top:4px;}
.chat-inp{display:flex;gap:8px;padding:12px;border-top:1px solid var(--bdr);background:#fff;}
.cinput{flex:1;background:var(--bg);border:1px solid var(--bdr);border-radius:8px;padding:10px 13px;font-size:13px;color:var(--text);font-family:'Plus Jakarta Sans',sans-serif;outline:none;resize:none;}
.cinput:focus{border-color:var(--red);background:#fff;}
.chat-hdr{display:flex;align-items:center;gap:10px;padding:13px 16px;border-bottom:1px solid var(--bdr);background:#fff;}
.modal{position:fixed;inset:0;background:rgba(0,0,0,0.45);z-index:500;display:none;align-items:flex-start;justify-content:center;padding:20px;overflow-y:auto;}
.modal.open{display:flex;}
.mbox{background:#fff;border:1px solid var(--bdr);border-radius:16px;width:100%;max-width:700px;margin:auto;box-shadow:var(--shadow-lg);}
.mhdr{display:flex;align-items:center;justify-content:space-between;padding:18px 22px;border-bottom:1px solid var(--bdr);}
.mbody{padding:22px;font-size:13px;line-height:1.95;color:var(--text);white-space:pre-line;max-height:62vh;overflow-y:auto;}
.mfoot{padding:14px 22px;border-top:1px solid var(--bdr);display:flex;align-items:center;justify-content:space-between;}
.pgn{display:flex;gap:8px;justify-content:center;margin-top:22px;}
.pgn-btn{width:38px;height:38px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;cursor:pointer;border:1px solid var(--bdr);background:#fff;color:var(--muted);transition:all 0.18s;text-decoration:none;box-shadow:var(--shadow);}
.pgn-btn:hover,.pgn-btn.active{background:var(--red);color:#fff;border-color:var(--red);}
.faq-item{border:1px solid var(--bdr);border-radius:10px;overflow:hidden;margin-bottom:8px;box-shadow:var(--shadow);}
.faq-q{padding:14px 18px;cursor:pointer;font-size:13px;font-weight:600;display:flex;justify-content:space-between;align-items:center;background:#fff;color:var(--text);transition:background 0.18s;}
.faq-q:hover{background:var(--red-light);}
.faq-a{display:none;padding:14px 18px;font-size:12px;color:var(--muted);line-height:1.85;border-top:1px solid var(--bdr);background:var(--bg);}
@keyframes fadeUp{from{opacity:0;transform:translateY(14px);}to{opacity:1;transform:none;}}
.fi{animation:fadeUp 0.45s ease forwards;}
.fi1{animation-delay:0.04s;opacity:0;}.fi2{animation-delay:0.1s;opacity:0;}.fi3{animation-delay:0.17s;opacity:0;}.fi4{animation-delay:0.24s;opacity:0;}.fi5{animation-delay:0.31s;opacity:0;}
.soc-icon{width:34px;height:34px;border-radius:7px;display:flex;align-items:center;justify-content:center;transition:all 0.18s;background:var(--red-light);border:1px solid var(--red-mid);}
.soc-icon:hover{background:var(--red);border-color:var(--red);}
.soc-icon:hover svg{stroke:#fff;}
.soc-icon svg{stroke:var(--red);}
@media(max-width:900px){.sb{width:200px;}.mc{margin-left:200px;padding:14px;}.g4{grid-template-columns:repeat(2,1fr);}.g3{grid-template-columns:1fr 1fr;}}
@media(max-width:640px){.sb{display:none;}.mc{margin-left:0;padding:11px;}.g4{grid-template-columns:repeat(2,1fr);}.g3{grid-template-columns:1fr;}.g2{grid-template-columns:1fr;}.topbar h1{font-size:16px;}}
</style>"""

def soc_sidebar():
    parts=[]
    for url,name,path in SOCIAL:
        parts.append(f'<a href="{url}" target="_blank" class="soc-icon" title="{name}"><svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="{path}"/></svg></a>')
    return '<div style="display:flex;gap:7px;flex-wrap:wrap;padding:10px 12px 14px;">'+("".join(parts))+'</div>'

def sidebar_html(active, user={}):
    name=user.get("name","Moderator")
    email=user.get("email","")
    notifs=get_notifs(email)
    nc=len(notifs)
    av=f'<img src="{user["avatar"]}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">' if user.get("avatar") else f'<span style="font-size:13px;font-weight:800;color:#fff;">{name[0].upper() if name else "M"}</span>'
    def ni(k,lb,ic,bg=""):
        cls="ni active" if active==k else "ni"
        badge=f'<span class="nbadge">{bg}</span>' if bg else ""
        return f'<a href="/{k}" class="{cls}">{ic}<span>{lb}</span>{badge}</a>'
    I=lambda p: f'<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" width="16" height="16"><path d="{p}"/></svg>'
    nav1=[
        ni("dashboard","Dashboard",I("M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z M9 22V12h6v10")),
        ni("jobs","Browse Jobs",I("M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"),"20"),
        ni("profile","My Profile",I("M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2 M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z")),
        ni("earnings","Earnings",I("M12 1v22 M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6")),
    ]
    nav2=[
        ni("notifications","Notifications",I("M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9 M13.73 21a2 2 0 0 1-3.46 0"),str(nc) if nc else ""),
        ni("schedule","My Schedule",I("M8 6h13 M8 12h13 M8 18h13 M3 6h.01 M3 12h.01 M3 18h.01")),
        ni("training","Training",I("M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"),"New"),
        ni("livechat","Live Support",I("M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z")),
        ni("support","Help & FAQ",I("M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3 M12 17h.01")),
    ]
    return f"""<div class="sb">
<div class="sb-logo"><h2>MODERATION SQUAD</h2><p>MODERATOR PORTAL</p></div>
<div style="padding:10px;border-bottom:1px solid var(--bdr);">
  <div style="display:flex;align-items:center;gap:9px;padding:10px;background:var(--red-light);border:1px solid var(--red-mid);border-radius:10px;">
    <div style="width:34px;height:34px;border-radius:50%;flex-shrink:0;background:linear-gradient(135deg,var(--red),var(--red2));display:flex;align-items:center;justify-content:center;overflow:hidden;">{av}</div>
    <div style="overflow:hidden;flex:1;"><div style="font-size:12px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--text);">{name}</div><div style="font-size:9px;color:var(--red);font-weight:700;">🔵 {user.get("level","Newcomer")}</div></div>
    <div style="width:7px;height:7px;border-radius:50%;background:var(--ok);box-shadow:0 0 5px var(--ok);flex-shrink:0;" title="Online"></div>
  </div>
</div>
<div class="nb-sec">Main</div>{"".join(nav1)}
<div class="nb-sec">Tools</div>{"".join(nav2)}
<div class="sb-bottom">
  {soc_sidebar()}
  <div class="sb-sup">
    <strong>📞 Support</strong>
    <div style="margin-top:5px;">📧 <a href="mailto:{S_EMAIL}">{S_EMAIL}</a></div>
    <div>📱 <a href="tel:{S_PHONE}">{S_PHONE}</a></div>
    <div style="font-size:10px;margin-top:3px;color:var(--muted);">Mon–Fri 9AM–6PM EST</div>
  </div>
  <a href="/logout" class="sb-logout">
    <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
    <span>Sign Out</span>
  </a>
</div>
</div>"""

def page(title, body, extra_head=""):
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Moderation Squad</title>{CSS}{extra_head}</head><body>{body}
<div class="toast" id="toast"></div>
<script>
function toast(msg,type='i'){{const t=document.getElementById('toast');t.textContent=msg;t.className='toast t'+type+' show';setTimeout(()=>t.className='toast',3200);}}
document.querySelectorAll('.faq-q').forEach(q=>q.addEventListener('click',()=>{{const a=q.nextElementSibling;a.style.display=a.style.display==='block'?'none':'block';q.querySelector('.faq-arr').textContent=a.style.display==='block'?'▲':'▼'}}));
</script></body></html>"""

# ── LANDING PAGE ──────────────────────────────────────────────
def landing():
    imgs=["https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=1400&q=80",
          "https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=1400&q=80",
          "https://images.unsplash.com/photo-1553877522-43269d4ea984?w=1400&q=80",
          "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=1400&q=80"]
    slides="".join(f'<div class="hsl" style="background-image:url(\'{u}\')"></div>' for u in imgs)
    soc_f="".join(f'<a href="{u}" target="_blank" style="width:36px;height:36px;border-radius:8px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);transition:all 0.2s;" title="{n}"><svg width="16" height="16" fill="none" stroke="white" stroke-width="2" viewBox="0 0 24 24"><path d="{p}"/></svg></a>' for u,n,p in SOCIAL)
    tests=[("Sarah K.","Texas, USA","Went from Newcomer to Elite in 8 months. Now earning $22/hr working from home full time. Life-changing!","⭐⭐⭐⭐⭐"),
           ("Marcus T.","California, USA","Training is excellent and the team is incredibly supportive. Got my first job within 2 weeks of joining.","⭐⭐⭐⭐⭐"),
           ("Aisha R.","New York, USA","Finally a platform that pays fairly and treats moderators like true professionals. Payouts are always on time.","⭐⭐⭐⭐⭐")]
    tests_h="".join(f'<div style="background:#fff;border:1px solid #e5e7eb;border-radius:16px;padding:26px;box-shadow:0 2px 12px rgba(0,0,0,0.05);"><p style="font-size:13px;color:#6b7280;line-height:1.85;margin-bottom:18px;font-style:italic;">"{q}"</p><div style="display:flex;align-items:center;gap:10px;"><div style="width:38px;height:38px;border-radius:50%;background:#C8332A;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:800;color:#fff;flex-shrink:0;">{n[0]}</div><div><div style="font-size:13px;font-weight:700;color:#1a0a0a;">{n}</div><div style="font-size:11px;color:#6b7280;">{lo}</div></div><div style="margin-left:auto;font-size:13px;">{st}</div></div></div>' for n,lo,q,st in tests)
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moderation Squad — Professional Chat Moderation</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
:root{{--red:#C8332A;--red2:#a01f18;}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:'Plus Jakarta Sans',sans-serif;background:#fff;color:#1a0a0a;overflow-x:hidden;}}
a{{text-decoration:none;color:inherit;}}
.btn{{display:inline-flex;align-items:center;gap:7px;padding:10px 22px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;border:none;transition:all 0.2s;font-family:'Plus Jakarta Sans',sans-serif;}}
.br{{background:var(--red);color:#fff;}}.br:hover{{background:var(--red2);transform:translateY(-1px);box-shadow:0 6px 20px rgba(200,51,42,0.35);}}
.bw{{background:#fff;color:var(--red);font-weight:700;}}.bw:hover{{background:#fde0de;}}
.nav{{display:flex;align-items:center;justify-content:space-between;padding:0 40px;height:66px;position:sticky;top:0;z-index:100;background:rgba(255,255,255,0.97);backdrop-filter:blur(14px);border-bottom:1px solid #e5e7eb;box-shadow:0 1px 12px rgba(0,0,0,0.06);}}
.nlogo{{display:flex;align-items:center;gap:10px;}}
.nltxt{{font-size:12px;font-weight:900;letter-spacing:2.5px;color:#1a0a0a;}}
.hero{{position:relative;height:100vh;overflow:hidden;display:flex;align-items:center;justify-content:center;}}
.hsl{{position:absolute;inset:0;background-size:cover;background-position:center;opacity:0;transition:opacity 1.4s ease;}}
.hsl.act{{opacity:1;}}
.hov{{position:absolute;inset:0;background:linear-gradient(135deg,rgba(26,5,5,0.88) 0%,rgba(200,51,42,0.22) 100%);}}
.hcnt{{position:relative;z-index:2;text-align:center;padding:0 20px;max-width:840px;}}
.hbdg{{font-size:10px;letter-spacing:4px;color:rgba(255,255,255,0.75);font-weight:700;text-transform:uppercase;margin-bottom:22px;padding:5px 18px;background:rgba(200,51,42,0.35);border:1px solid rgba(200,51,42,0.55);border-radius:999px;display:inline-block;}}
.hcnt h1{{font-size:clamp(32px,6.5vw,72px);font-weight:800;color:#fff;line-height:1.05;margin-bottom:20px;letter-spacing:-2px;}}
.hcnt h1 em{{font-style:normal;color:#ff8a7a;}}
.hcnt p{{font-size:clamp(14px,2vw,18px);color:rgba(255,255,255,0.72);max-width:520px;margin:0 auto 36px;line-height:1.85;}}
.hbtns{{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;}}
.hdots{{position:absolute;bottom:28px;left:50%;transform:translateX(-50%);display:flex;gap:8px;z-index:3;}}
.hdot{{width:8px;height:8px;border-radius:50%;background:rgba(255,255,255,0.35);cursor:pointer;transition:all 0.3s;border:none;}}
.hdot.act{{background:#fff;width:26px;border-radius:4px;}}
.sbar{{background:var(--red);padding:22px 40px;display:flex;justify-content:center;gap:64px;flex-wrap:wrap;}}
.si{{text-align:center;}}.si h3{{font-size:28px;font-weight:800;color:#fff;letter-spacing:-1px;}}.si p{{font-size:11px;color:rgba(255,255,255,0.72);margin-top:2px;letter-spacing:1px;}}
.sec{{padding:80px 40px;max-width:1100px;margin:0 auto;}}
.st{{font-size:clamp(24px,4vw,38px);font-weight:800;text-align:center;margin-bottom:10px;letter-spacing:-1px;}}.st span{{color:var(--red);}}
.ss{{text-align:center;color:#6b7280;font-size:14px;margin-bottom:52px;}}
.feat-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:20px;}}
.fc{{background:#fff;border:1px solid #e5e7eb;border-radius:16px;padding:26px;transition:all 0.3s;box-shadow:0 1px 4px rgba(0,0,0,0.05);}}
.fc:hover{{border-color:var(--red);transform:translateY(-4px);box-shadow:0 16px 40px rgba(200,51,42,0.1);}}
.fic{{width:46px;height:46px;border-radius:12px;margin-bottom:16px;background:#fff0ef;display:flex;align-items:center;justify-content:center;font-size:22px;}}
.fc h3{{font-size:15px;font-weight:700;margin-bottom:7px;}}.fc p{{font-size:12px;color:#6b7280;line-height:1.75;}}
.bg-light{{background:#f8f9fa;padding:80px 40px;}}
.dsec{{background:linear-gradient(135deg,#1a0505,#2d0f0f);padding:80px 40px;text-align:center;}}
.dsec h2{{font-size:32px;font-weight:800;color:#fff;margin-bottom:12px;letter-spacing:-1px;}}.dsec p{{color:rgba(255,255,255,0.6);font-size:15px;margin-bottom:30px;}}
footer{{background:#1a0505;padding:44px 40px;}}
.fg{{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:32px;max-width:1100px;margin:0 auto 32px;}}
.flogo{{font-size:12px;font-weight:900;letter-spacing:3px;color:var(--red);margin-bottom:10px;}}
.fdesc{{font-size:12px;color:rgba(255,255,255,0.38);line-height:1.75;}}
.fcol h4{{font-size:10px;letter-spacing:2px;color:rgba(255,255,255,0.4);text-transform:uppercase;margin-bottom:13px;}}
.fcol a{{display:block;font-size:12px;color:rgba(255,255,255,0.38);margin-bottom:8px;transition:color 0.2s;}}.fcol a:hover{{color:var(--red);}}
.fbot{{max-width:1100px;margin:0 auto;padding-top:24px;border-top:1px solid rgba(255,255,255,0.07);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;}}
.fbot p{{font-size:11px;color:rgba(255,255,255,0.25);}}
@media(max-width:768px){{.nlinks{{display:none;}}.sec{{padding:52px 16px;}}.sbar{{gap:28px;padding:18px 16px;}}.fg{{grid-template-columns:1fr 1fr;}}}}
</style></head><body>
<nav class="nav">
  <div class="nlogo"><div style="width:32px;height:32px;border-radius:8px;background:#C8332A;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:900;color:#fff;">M</div><span class="nltxt">MODERATION SQUAD</span></div>
  <div style="display:flex;gap:10px;align-items:center;">
    <div style="display:flex;gap:8px;">{soc_f}</div>
    <a href="/login" class="btn br" style="font-size:12px;padding:8px 18px;">Sign In →</a>
  </div>
</nav>
<section class="hero">
  <div class="hsl act" style="background-image:url('{imgs[0]}')"></div>
  {"".join(f'<div class="hsl" style="background-image:url(\'{u}\')"></div>' for u in imgs[1:])}
  <div class="hov"></div>
  <div class="hcnt">
    <div class="hbdg">🛡️ TRUSTED BY 15,000+ MODERATORS WORLDWIDE</div>
    <h1>Your Career in<br><em>Content Moderation</em><br>Starts Here</h1>
    <p>Join the world's most trusted moderation platform. Work remotely, get paid weekly, and build a career protecting online communities.</p>
    <div class="hbtns"><a href="/login" class="btn br" style="font-size:14px;padding:13px 28px;">Get Started Free →</a><a href="#how" class="btn bw" style="font-size:14px;padding:13px 28px;">How It Works</a></div>
  </div>
</section>
<div class="sbar">
  <div class="si"><h3>15,000+</h3><p>ACTIVE MODERATORS</p></div>
  <div class="si"><h3>500+</h3><p>PARTNER BRANDS</p></div>
  <div class="si"><h3>$5–$22</h3><p>HOURLY PAY RANGE</p></div>
  <div class="si"><h3>100%</h3><p>REMOTE WORK</p></div>
  <div class="si"><h3>Weekly</h3><p>GUARANTEED PAYOUTS</p></div>
</div>
<section class="sec">
  <p class="st">Why Choose <span>Moderation Squad?</span></p>
  <p class="ss">Everything you need to launch and grow a professional moderation career</p>
  <div class="feat-grid">
    <div class="fc"><div class="fic">💰</div><h3>Competitive Weekly Pay</h3><p>Earn $5–$22/hr based on your level. Payments every Friday via Direct Deposit, PayPal, or Payoneer.</p></div>
    <div class="fc"><div class="fic">🏠</div><h3>100% Remote Work</h3><p>Work from anywhere in the world. Set your own schedule with flexible hours that fit your life.</p></div>
    <div class="fc"><div class="fic">📈</div><h3>Clear Career Path</h3><p>Progress from Newcomer to Elite through Newcomer → Junior → Senior → Elite with increasing pay.</p></div>
    <div class="fc"><div class="fic">🎓</div><h3>Professional Training</h3><p>Free certification courses in chat moderation, content policy, trust & safety, and more.</p></div>
    <div class="fc"><div class="fic">🛡️</div><h3>Verified & Secure</h3><p>Background-checked team. Secure OTP login. Your data and earnings are always protected.</p></div>
    <div class="fc"><div class="fic">🤝</div><h3>Dedicated Support</h3><p>Our team is available Mon–Fri 9AM–6PM EST for account, payment, and job placement support.</p></div>
  </div>
</section>
<div class="bg-light" id="how">
  <div style="max-width:1100px;margin:0 auto;">
    <p class="st">How It <span>Works</span></p>
    <p class="ss">Get started in minutes and start earning this week</p>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:0;">
      <div style="text-align:center;padding:32px 18px;"><div style="width:52px;height:52px;border-radius:50%;background:#C8332A;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:800;color:#fff;margin:0 auto 14px;">1</div><h3 style="font-size:14px;font-weight:700;margin-bottom:7px;">Apply & Verify</h3><p style="font-size:12px;color:#6b7280;line-height:1.75;">Create your account with your approved email. Complete identity and background verification.</p></div>
      <div style="text-align:center;padding:32px 18px;"><div style="width:52px;height:52px;border-radius:50%;background:#C8332A;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:800;color:#fff;margin:0 auto 14px;">2</div><h3 style="font-size:14px;font-weight:700;margin-bottom:7px;">Complete Training</h3><p style="font-size:12px;color:#6b7280;line-height:1.75;">Take our free certification courses to qualify for moderation positions and improve your skills.</p></div>
      <div style="text-align:center;padding:32px 18px;"><div style="width:52px;height:52px;border-radius:50%;background:#C8332A;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:800;color:#fff;margin:0 auto 14px;">3</div><h3 style="font-size:14px;font-weight:700;margin-bottom:7px;">Apply for Jobs</h3><p style="font-size:12px;color:#6b7280;line-height:1.75;">Browse available positions and apply for roles that match your schedule and skill level.</p></div>
      <div style="text-align:center;padding:32px 18px;"><div style="width:52px;height:52px;border-radius:50%;background:#C8332A;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:800;color:#fff;margin:0 auto 14px;">4</div><h3 style="font-size:14px;font-weight:700;margin-bottom:7px;">Get Paid Weekly</h3><p style="font-size:12px;color:#6b7280;line-height:1.75;">Earn competitive hourly rates and receive guaranteed weekly payments every Friday.</p></div>
    </div>
  </div>
</div>
<section class="sec">
  <p class="st">What Our <span>Moderators Say</span></p>
  <p class="ss">Join thousands of professionals already building their careers</p>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;">{tests_h}</div>
</section>
<div class="dsec">
  <h2>Ready to Start Your Moderation Career?</h2>
  <p>Join 15,000+ moderators already earning with Moderation Squad</p>
  <a href="/login" class="btn bw" style="font-size:14px;padding:13px 32px;">Apply Now — It's Free →</a>
</div>
<footer>
  <div class="fg">
    <div><div class="flogo">MODERATION SQUAD</div><p class="fdesc">The world's most trusted platform for professional content moderation careers. 100% remote. Paid weekly.</p><div style="display:flex;gap:8px;margin-top:16px;">{soc_f}</div></div>
    <div class="fcol"><h4>Platform</h4><a href="/login">Sign In</a><a href="#">Browse Jobs</a><a href="#">Training</a><a href="#">Earnings</a></div>
    <div class="fcol"><h4>Company</h4><a href="https://www.modsquad.com/about/" target="_blank">About</a><a href="https://www.modsquad.com/blog/" target="_blank">Blog</a><a href="https://www.modsquad.com/careers/" target="_blank">Careers</a></div>
    <div class="fcol"><h4>Support</h4><a href="mailto:{S_EMAIL}">{S_EMAIL}</a><a href="tel:{S_PHONE}">{S_PHONE}</a><a href="#">Help Center</a></div>
  </div>
  <div class="fbot"><p>© 2025 Moderation Squad. All rights reserved.</p><p>Privacy Policy · Terms of Service · Cookie Policy</p></div>
</footer>
<script>
const slides=document.querySelectorAll('.hsl');let cur=0;
setInterval(()=>{{slides[cur].classList.remove('act');cur=(cur+1)%slides.length;slides[cur].classList.add('act');}},5000);
</script>
</body></html>"""

# ── LOGIN PAGE ────────────────────────────────────────────────
def login_pg():
    return """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign In — Moderation Squad</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Plus Jakarta Sans',sans-serif;background:linear-gradient(135deg,#1a0505 0%,#2d0f0f 50%,#1a0505 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;}
.box{background:#fff;border-radius:20px;padding:44px;width:100%;max-width:420px;box-shadow:0 24px 64px rgba(0,0,0,0.3);}
.logo{text-align:center;margin-bottom:32px;}
.logo-icon{width:54px;height:54px;border-radius:14px;background:#C8332A;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:900;color:#fff;margin:0 auto 12px;}
.logo h1{font-size:13px;font-weight:900;letter-spacing:3px;color:#1a0a0a;}
.logo p{font-size:11px;color:#6b7280;margin-top:4px;}
.step{display:none;}.step.act{display:block;}
label{font-size:11px;font-weight:600;color:#6b7280;letter-spacing:0.5px;text-transform:uppercase;display:block;margin-bottom:6px;}
input{width:100%;border:1px solid #e5e7eb;border-radius:9px;padding:12px 14px;font-size:14px;font-family:'Plus Jakarta Sans',sans-serif;outline:none;transition:all 0.18s;color:#1a0a0a;}
input:focus{border-color:#C8332A;box-shadow:0 0 0 3px rgba(200,51,42,0.08);}
.btn{width:100%;padding:13px;border-radius:9px;font-size:14px;font-weight:700;cursor:pointer;border:none;font-family:'Plus Jakarta Sans',sans-serif;transition:all 0.18s;margin-top:16px;}
.bp{background:#C8332A;color:#fff;}.bp:hover{background:#a01f18;}
.err{background:#fef2f2;border:1px solid #fecaca;color:#dc2626;border-radius:8px;padding:11px 14px;font-size:12px;margin-top:12px;display:none;}
.otp-wrap{display:flex;gap:8px;justify-content:center;margin:20px 0;}
.otp-wrap input{width:48px;height:54px;text-align:center;font-size:22px;font-weight:700;padding:0;border-radius:10px;}
.hint{font-size:12px;color:#6b7280;text-align:center;margin-top:14px;line-height:1.7;}
.back{background:none;border:none;color:#C8332A;font-size:12px;font-weight:600;cursor:pointer;font-family:'Plus Jakarta Sans',sans-serif;margin-top:10px;width:100%;text-align:center;}
</style></head><body>
<div class="box">
  <div class="logo">
    <div class="logo-icon">M</div>
    <h1>MODERATION SQUAD</h1>
    <p>Moderator Portal — Secure Sign In</p>
  </div>
  <div class="step act" id="s1">
    <div style="margin-bottom:16px;"><label>Work Email Address</label><input type="email" id="email" placeholder="yourname@email.com" autocomplete="email"></div>
    <div id="err1" class="err"></div>
    <button class="btn bp" onclick="sendOtp()">Send Secure Code →</button>
    <p class="hint">A 6-digit code will be sent to your email.<br>Only approved moderators can access this portal.</p>
  </div>
  <div class="step" id="s2">
    <p style="font-size:13px;color:#6b7280;margin-bottom:20px;text-align:center;">Enter the 6-digit code sent to<br><strong id="emailShow" style="color:#1a0a0a;"></strong></p>
    <div class="otp-wrap">
      <input type="tel" maxlength="1" class="otp" id="o0">
      <input type="tel" maxlength="1" class="otp" id="o1">
      <input type="tel" maxlength="1" class="otp" id="o2">
      <input type="tel" maxlength="1" class="otp" id="o3">
      <input type="tel" maxlength="1" class="otp" id="o4">
      <input type="tel" maxlength="1" class="otp" id="o5">
    </div>
    <div id="err2" class="err"></div>
    <button class="btn bp" onclick="verifyOtp()">Verify & Sign In →</button>
    <button class="back" onclick="document.getElementById('s1').className='step act';document.getElementById('s2').className='step';">← Use a different email</button>
  </div>
</div>
<script>
let userEmail='';
function showErr(id,msg){const e=document.getElementById(id);e.textContent=msg;e.style.display='block';}
function hideErr(id){document.getElementById(id).style.display='none';}
async function sendOtp(){
  const email=document.getElementById('email').value.trim();
  if(!email){showErr('err1','Please enter your email address.');return;}
  hideErr('err1');
  const btn=document.querySelector('#s1 .btn');btn.textContent='Sending...';btn.disabled=true;
  const r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email})});
  const d=await r.json();
  btn.textContent='Send Secure Code →';btn.disabled=false;
  if(d.success){userEmail=email;document.getElementById('emailShow').textContent=email;document.getElementById('s1').className='step';document.getElementById('s2').className='step act';document.getElementById('o0').focus();}
  else showErr('err1',d.message||'Access denied.');
}
document.querySelectorAll('.otp').forEach((inp,i)=>{
  inp.addEventListener('input',()=>{if(inp.value&&i<5)document.getElementById('o'+(i+1)).focus();});
  inp.addEventListener('keydown',e=>{if(e.key==='Backspace'&&!inp.value&&i>0)document.getElementById('o'+(i-1)).focus();});
});
async function verifyOtp(){
  const code=[...Array(6)].map((_,i)=>document.getElementById('o'+i).value).join('');
  if(code.length<6){showErr('err2','Please enter all 6 digits.');return;}
  hideErr('err2');
  const btn=document.querySelector('#s2 .bp');btn.textContent='Verifying...';btn.disabled=true;
  const r=await fetch('/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:userEmail,code})});
  const d=await r.json();
  btn.textContent='Verify & Sign In →';btn.disabled=false;
  if(d.success)window.location='/dashboard';
  else showErr('err2',d.message||'Invalid code.');
}
document.getElementById('email').addEventListener('keydown',e=>{if(e.key==='Enter')sendOtp();});
</script></body></html>"""

# ── DASHBOARD ─────────────────────────────────────────────────
def dash_pg(user):
    name=user.get("name","Moderator")
    applied=user.get("applied_jobs",[])
    notifs=get_notifs(user.get("email",""))
    nc=len(notifs)
    jobs_done=user.get("jobs_done",0)
    earned=user.get("earned",0.0)
    level=user.get("level","Newcomer")
    next_lvl=6 if level=="Newcomer" else 21 if level=="Junior" else 50 if level=="Senior" else 100
    prog=min(100,int(jobs_done/next_lvl*100))
    recent_jobs="".join(f'''<tr><td style="padding:11px 14px;font-size:13px;font-weight:600;">{j["title"]}</td>
<td style="padding:11px 14px;font-size:12px;color:#6b7280;">{j["company"]}</td>
<td style="padding:11px 14px;"><span style="background:#fffbeb;color:#d97706;border:1px solid #fde68a;font-size:10px;font-weight:700;padding:3px 10px;border-radius:999px;">{j["status"]}</span></td>
<td style="padding:11px 14px;font-size:12px;color:#C8332A;font-weight:700;">{j["pay"]}</td>
<td style="padding:11px 14px;font-size:11px;color:#6b7280;">{j["date"]}</td>
</tr>''' for j in applied[-5:]) or '<tr><td colspan="5" style="padding:20px;text-align:center;color:#6b7280;font-size:13px;">No applications yet. <a href="/jobs" style="color:#C8332A;font-weight:600;">Browse Jobs →</a></td></tr>'
    notif_html="".join(f'<div style="padding:10px 14px;border-bottom:1px solid var(--bdr);"><div style="font-size:12px;color:var(--text);line-height:1.6;">{n["msg"]}</div><div style="font-size:10px;color:var(--muted);margin-top:3px;">{n["time"]}</div></div>' for n in notifs[:5]) or '<div style="padding:16px;text-align:center;color:var(--muted);font-size:12px;">No notifications yet</div>'
    body=f"""{sidebar_html("dashboard",user)}
<div class="mc">
<div class="topbar">
  <div><h1>👋 Welcome back, {name.split()[0]}!</h1><p>{datetime.now().strftime("%A, %B %d, %Y")} · Moderation Squad Portal</p></div>
  <div class="tr">
    <span class="bdg b-red">🔵 {level}</span>
    <div style="position:relative;">
      <div class="nbell" onclick="document.getElementById('nd').classList.toggle('open')">
        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" width="18" height="18"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9 M13.73 21a2 2 0 0 1-3.46 0"/></svg>
        {"<div class='ndot'></div>" if nc else ""}
      </div>
      <div class="ndrop" id="nd">
        <div style="padding:12px 14px;border-bottom:1px solid var(--bdr);font-size:12px;font-weight:700;">Notifications ({nc})</div>
        {notif_html}
        <div style="padding:10px;text-align:center;"><a href="/notifications" style="font-size:12px;color:var(--red);font-weight:600;">View All →</a></div>
      </div>
    </div>
    <a href="/jobs" class="btn bp bsm">+ Apply for Jobs</a>
  </div>
</div>
<div class="g4 fi fi1">
  <div class="sc c1"><div class="sl">Applications</div><div class="sv">{len(applied)}</div><div class="ss2">Total submitted</div><div class="si2">💼</div></div>
  <div class="sc c2"><div class="sl">Jobs Completed</div><div class="sv">{jobs_done}</div><div class="ss2">Confirmed</div><div class="si2">✅</div></div>
  <div class="sc c3"><div class="sl">Total Earned</div><div class="sv">${earned:.2f}</div><div class="ss2">All time</div><div class="si2">💵</div></div>
  <div class="sc c4"><div class="sl">Level Progress</div><div class="sv">{prog}%</div><div class="ss2">to next level</div><div class="si2">🏆</div></div>
</div>
<div class="g2 fi fi2" style="margin-top:16px;">
  <div class="card">
    <div class="sh"><h2>Level Progress</h2><span class="bdg b-red">{level}</span></div>
    <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-bottom:7px;"><span>{jobs_done} jobs</span><span>{next_lvl} jobs needed</span></div>
    <div class="pb"><div class="pf" style="width:{prog}%"></div></div>
    <p style="font-size:11px;color:var(--muted);margin-top:10px;">Complete {max(0,next_lvl-jobs_done)} more jobs to unlock the next level and higher-paying positions.</p>
    <a href="/jobs" class="btn bp bsm" style="margin-top:14px;width:100%;justify-content:center;">Browse Open Positions →</a>
  </div>
  <div class="card">
    <div class="sh"><h2>Quick Actions</h2></div>
    <div style="display:flex;flex-direction:column;gap:8px;">
      <a href="/jobs" class="btn bo" style="justify-content:flex-start;gap:10px;">💼 Browse Jobs (20 Open)</a>
      <a href="/training" class="btn bo" style="justify-content:flex-start;gap:10px;">📚 Continue Training</a>
      <a href="/profile" class="btn bo" style="justify-content:flex-start;gap:10px;">👤 Complete Profile</a>
      <a href="/earnings" class="btn bo" style="justify-content:flex-start;gap:10px;">💰 View Earnings</a>
      <a href="/schedule" class="btn bo" style="justify-content:flex-start;gap:10px;">📅 Set My Schedule</a>
      <a href="/livechat" class="btn bo" style="justify-content:flex-start;gap:10px;">💬 Live Support Chat</a>
    </div>
  </div>
</div>
<div class="card fi fi3" style="margin-top:16px;">
  <div class="sh"><h2>Recent Applications</h2><a href="/jobs" class="btn bo bsm">View All Jobs</a></div>
  <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;">
      <thead><tr style="border-bottom:2px solid var(--bdr);">
        <th style="text-align:left;padding:10px 14px;font-size:10px;letter-spacing:1.5px;color:var(--muted);text-transform:uppercase;">Position</th>
        <th style="text-align:left;padding:10px 14px;font-size:10px;letter-spacing:1.5px;color:var(--muted);text-transform:uppercase;">Company</th>
        <th style="text-align:left;padding:10px 14px;font-size:10px;letter-spacing:1.5px;color:var(--muted);text-transform:uppercase;">Status</th>
        <th style="text-align:left;padding:10px 14px;font-size:10px;letter-spacing:1.5px;color:var(--muted);text-transform:uppercase;">Pay</th>
        <th style="text-align:left;padding:10px 14px;font-size:10px;letter-spacing:1.5px;color:var(--muted);text-transform:uppercase;">Date</th>
      </tr></thead>
      <tbody>{recent_jobs}</tbody>
    </table>
  </div>
</div>
</div>"""
    return page("Dashboard",f'<div class="layout">{body}</div>')

# ── JOBS PAGE ─────────────────────────────────────────────────
def jobs_pg(user, pg=1):
    applied_titles=[j["title"] for j in user.get("applied_jobs",[])]
    page_jobs=[j for j in ALL_JOBS if j["pg"]==pg]
    cards=""
    for j in page_jobs:
        applied=j["title"] in applied_titles
        lk=" lk" if j["locked"] else ""
        req_badge=f'<span class="tg tl">{j.get("req","")}</span>' if j.get("locked") else '<span class="tg tp">✅ Open Now</span>'
        apply_btn=f'<button class="btn bs bsm" disabled>✅ Applied</button>' if applied else (f'<button class="btn bl bsm" disabled>🔒 Locked</button>' if j["locked"] else f'<button class="btn bp bsm" onclick="applyJob(this,\'{j["title"]}\',\'{j["company"]}\',\'{j["pay"]}\')">Apply Now →</button>')
        cards+=f'''<div class="jc{lk}">
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
  <span style="font-size:22px;">{j["icon"]}</span>
  {'<span class="tg tn">🔒 Locked</span>' if j["locked"] else '<span class="tg tp">● OPEN</span>'}
</div>
<div class="jt">{j["title"]}</div>
<div class="jco">🏢 {j["company"]}</div>
<div class="jd">{j["desc"]}</div>
<div class="jm"><span class="tg tp">{j["pay"]}</span><span class="tg tt">⏱ {j["hrs"]}</span>{req_badge}</div>
{apply_btn}
</div>'''
    pgn="".join(f'<a href="/jobs?pg={i}" class="pgn-btn{"active" if i==pg else ""}">{i}</a>' for i in range(1,5))
    body=f"""{sidebar_html("jobs",user)}
<div class="mc">
<div class="topbar"><div><h1>💼 Browse Jobs</h1><p>20 positions across 4 pages · Apply directly from here</p></div>
<div class="tr"><span class="bdg b-green">20 Open Positions</span></div></div>
<div style="background:linear-gradient(135deg,#fff0ef,#fde0de);border:1px solid var(--red-mid);border-radius:14px;padding:16px 20px;margin-bottom:20px;display:flex;align-items:center;gap:14px;">
  <span style="font-size:22px;">💡</span>
  <div><div style="font-size:13px;font-weight:700;">Unlock more jobs by completing applications!</div>
  <div style="font-size:12px;color:var(--muted);margin-top:3px;">Newcomer: 3 jobs open · Complete 6 to unlock Junior (10 more jobs) · Complete 21 for Senior · 50 for Elite</div></div>
</div>
<div class="g3 fi fi1">{cards}</div>
<div class="pgn">{pgn}</div>
</div>
<div class="modal" id="modal"><div class="mbox">
  <div class="mhdr"><h3 id="mtitle" style="font-size:15px;font-weight:700;"></h3><button onclick="document.getElementById('modal').className='modal'" style="background:none;border:none;font-size:20px;cursor:pointer;color:var(--muted);">×</button></div>
  <div class="mbody" id="mbody"></div>
  <div class="mfoot"><span class="bdg b-green" id="mstatus">● Under Review</span><button class="btn bp" id="mconfirm">Confirm Application →</button></div>
</div></div>"""
    return page("Browse Jobs",f'<div class="layout">{body}</div>',"""<script>
let pendingJob=null;
function applyJob(btn,title,company,pay){pendingJob={title,company,pay};document.getElementById('mtitle').textContent='Apply: '+title;document.getElementById('mbody').textContent='You are applying for '+title+' at '+company+'.\n\nPay: '+pay+'\n\nYour application will be reviewed within 1-3 business days. You will receive an email confirmation.';document.getElementById('modal').className='modal open';}
document.getElementById('mconfirm').addEventListener('click',async()=>{
if(!pendingJob)return;
document.getElementById('mconfirm').textContent='Submitting...';document.getElementById('mconfirm').disabled=true;
const r=await fetch('/apply_job',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(pendingJob)});
const d=await r.json();
if(d.success){document.getElementById('modal').className='modal';toast('✅ Application submitted! Check your email.','s');setTimeout(()=>location.reload(),1500);}
else toast('Error submitting. Please try again.','e');
document.getElementById('mconfirm').textContent='Confirm Application →';document.getElementById('mconfirm').disabled=false;
pendingJob=null;
});
</script>""")

# ── PROFILE PAGE ──────────────────────────────────────────────
def profile_pg(user):
    name=user.get("name","Moderator")
    email=user.get("email","")
    level=user.get("level","Newcomer")
    since=user.get("member_since","")
    verifs=user.get("verifications",{})
    av=f'<img src="{user["avatar"]}" style="width:100%;height:100%;object-fit:cover;">' if user.get("avatar") else f'<span style="font-size:28px;font-weight:800;color:#fff;">{name[0].upper() if name else "M"}</span>'
    def vi(icon,label,note,ok):
        cls="vd-bg" if ok else "vw-bg"
        vst="vst-ok" if ok else "vst-warn"
        vstxt="✅ Verified" if ok else "⚠️ Pending"
        return f'<div class="vi"><div class="vl"><div class="vic {cls}">{icon}</div><div><div class="vn">{label}</div><div class="vs2">{note}</div></div></div><span class="vst {vst}">{vstxt}</span></div>'
    body=f"""{sidebar_html("profile",user)}
<div class="mc">
<div class="topbar"><div><h1>👤 My Profile</h1><p>Manage your account and verification status</p></div></div>
<div class="g2 fi fi1">
  <div class="card">
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;">
      <div class="avw">
        <div class="av">{av}</div>
        <div class="ave" onclick="document.getElementById('fi').click()">📷</div>
        <input type="file" id="fi" accept="image/*" style="display:none" onchange="uploadAvatar(this)">
      </div>
      <div><div style="font-size:18px;font-weight:800;">{name}</div>
      <div style="font-size:12px;color:var(--muted);margin-top:3px;">{email}</div>
      <div class="bdg b-red" style="margin-top:8px;">🔵 {level} Moderator</div></div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
      <div style="background:var(--bg);border-radius:10px;padding:12px;border:1px solid var(--bdr);"><div style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;">Member Since</div><div style="font-size:14px;font-weight:700;margin-top:4px;">{since}</div></div>
      <div style="background:var(--bg);border-radius:10px;padding:12px;border:1px solid var(--bdr);"><div style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;">Current Level</div><div style="font-size:14px;font-weight:700;margin-top:4px;">{level}</div></div>
      <div style="background:var(--bg);border-radius:10px;padding:12px;border:1px solid var(--bdr);"><div style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;">Applications</div><div style="font-size:14px;font-weight:700;margin-top:4px;">{len(user.get("applied_jobs",[]))}</div></div>
      <div style="background:var(--bg);border-radius:10px;padding:12px;border:1px solid var(--bdr);"><div style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;">Jobs Done</div><div style="font-size:14px;font-weight:700;margin-top:4px;">{user.get("jobs_done",0)}</div></div>
    </div>
  </div>
  <div class="card">
    <div class="sh"><h2>Verification Status</h2></div>
    {vi("📧","Email Address","Work email verified via OTP",verifs.get("email",True))}
    {vi("🏠","Proof of Residence","Address document on file",verifs.get("residence",True))}
    {vi("🪪","Government ID","Identity document verified",verifs.get("id",True))}
    {vi("📋","W-9 Tax Form","Tax form on file",verifs.get("tax",True))}
    {vi("💳","Payment Method","Set up in Earnings section",verifs.get("payment",False))}
    {vi("🔍","Background Check","Professional background check",verifs.get("background",True))}
  </div>
</div>
<div class="card fi fi2" style="margin-top:16px;">
  <div class="sh"><h2>Edit Profile</h2></div>
  <div class="g2">
    <div class="form-group"><label class="form-label">Full Name</label><input class="form-input" id="fn" value="{name}"></div>
    <div class="form-group"><label class="form-label">Email</label><input class="form-input" value="{email}" disabled style="background:var(--bg);color:var(--muted);"></div>
  </div>
  <button class="btn bp" onclick="saveName()">Save Changes</button>
</div>
</div>"""
    return page("My Profile",f'<div class="layout">{body}</div>',"""<script>
function uploadAvatar(input){
  const f=input.files[0];if(!f)return;
  const r=new FileReader();r.onload=async e=>{
    const d=await fetch('/upload_avatar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image:e.target.result})});
    const j=await d.json();if(j.success){toast('Profile picture updated!','s');setTimeout(()=>location.reload(),1000);}
  };r.readAsDataURL(f);
}
async function saveName(){
  const name=document.getElementById('fn').value.trim();
  if(!name){toast('Name cannot be empty','e');return;}
  const r=await fetch('/update_profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
  const d=await r.json();if(d.success)toast('Profile updated!','s');
}
</script>""")

# ── EARNINGS PAGE ─────────────────────────────────────────────
def earnings_pg(user):
    earned=user.get("earned",0.0)
    applied=user.get("applied_jobs",[])
    body=f"""{sidebar_html("earnings",user)}
<div class="mc">
<div class="topbar"><div><h1>💰 Earnings</h1><p>Your payment history and payout settings</p></div></div>
<div class="g4 fi fi1">
  <div class="sc c1"><div class="sl">Total Earned</div><div class="sv">${earned:.2f}</div><div class="ss2">All time</div><div class="si2">💵</div></div>
  <div class="sc c2"><div class="sl">Pending</div><div class="sv">$0.00</div><div class="ss2">Processing</div><div class="si2">⏳</div></div>
  <div class="sc c3"><div class="sl">Last Payout</div><div class="sv">$0.00</div><div class="ss2">No payouts yet</div><div class="si2">🏦</div></div>
  <div class="sc c4"><div class="sl">Next Payout</div><div class="sv">Friday</div><div class="ss2">Weekly schedule</div><div class="si2">📅</div></div>
</div>
<div class="g2 fi fi2" style="margin-top:16px;">
  <div class="card">
    <div class="sh"><h2>Payment Method</h2></div>
    <div style="background:var(--warn-bg);border:1px solid var(--warn-bdr);border-radius:10px;padding:14px;margin-bottom:16px;">
      <div style="font-size:13px;font-weight:700;color:var(--warn);">⚠️ Payment method not set up</div>
      <div style="font-size:12px;color:var(--muted);margin-top:4px;">Set up your payment method to receive earnings every Friday.</div>
    </div>
    <div style="display:flex;flex-direction:column;gap:8px;">
      <button class="btn bp" onclick="toast('Payment setup will be available once you complete your first assignment.','i')">Set Up Direct Deposit (ACH)</button>
      <button class="btn bo" onclick="toast('PayPal setup will be available once you complete your first assignment.','i')">Connect PayPal</button>
      <button class="btn bo" onclick="toast('Payoneer setup will be available once you complete your first assignment.','i')">Connect Payoneer</button>
    </div>
  </div>
  <div class="card">
    <div class="sh"><h2>Payout Schedule</h2></div>
    <div style="display:flex;flex-direction:column;gap:10px;">
      <div style="background:var(--bg);border-radius:10px;padding:13px;border:1px solid var(--bdr);"><div style="font-size:12px;font-weight:700;">📅 Weekly Payouts</div><div style="font-size:11px;color:var(--muted);margin-top:3px;">Every Friday for the prior week's work</div></div>
      <div style="background:var(--bg);border-radius:10px;padding:13px;border:1px solid var(--bdr);"><div style="font-size:12px;font-weight:700;">💵 Minimum Payout</div><div style="font-size:11px;color:var(--muted);margin-top:3px;">$10 minimum balance required</div></div>
      <div style="background:var(--bg);border-radius:10px;padding:13px;border:1px solid var(--bdr);"><div style="font-size:12px;font-weight:700;">🔒 Secure Processing</div><div style="font-size:11px;color:var(--muted);margin-top:3px;">Bank-level encryption on all transactions</div></div>
    </div>
  </div>
</div>
<div class="card fi fi3" style="margin-top:16px;">
  <div class="sh"><h2>Application History</h2></div>
  {"".join(f'<div style="display:flex;align-items:center;justify-content:space-between;padding:12px 0;border-bottom:1px solid var(--bdr);"><div><div style="font-size:13px;font-weight:600;">{j["title"]}</div><div style="font-size:11px;color:var(--muted);">{j["company"]} · {j["date"]}</div></div><span style="color:var(--red);font-weight:700;font-size:13px;">{j["pay"]}</span></div>' for j in applied) or '<div style="text-align:center;padding:24px;color:var(--muted);font-size:13px;">No applications yet. <a href="/jobs" style="color:var(--red);">Browse Jobs →</a></div>'}
</div>
</div>"""
    return page("Earnings",f'<div class="layout">{body}</div>')

# ── NOTIFICATIONS ─────────────────────────────────────────────
def notif_pg(user):
    notifs=get_notifs(user.get("email",""))
    items="".join(f'<div style="display:flex;gap:12px;padding:14px;border-bottom:1px solid var(--bdr);"><div style="width:36px;height:36px;border-radius:50%;background:var(--red-light);display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;">🔔</div><div><div style="font-size:13px;line-height:1.6;">{n["msg"]}</div><div style="font-size:11px;color:var(--muted);margin-top:4px;">{n["time"]}</div></div></div>' for n in notifs) or '<div style="padding:40px;text-align:center;color:var(--muted);font-size:13px;">No notifications yet. Start by browsing and applying for jobs!</div>'
    body=f"""{sidebar_html("notifications",user)}
<div class="mc">
<div class="topbar"><div><h1>🔔 Notifications</h1><p>Your activity feed and updates</p></div><span class="bdg b-red">{len(notifs)} total</span></div>
<div class="card fi fi1">{items}</div>
</div>"""
    return page("Notifications",f'<div class="layout">{body}</div>')

# ── SCHEDULE PAGE ─────────────────────────────────────────────
def schedule_pg(user):
    days=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    slots=["6AM–10AM","10AM–2PM","2PM–6PM","6PM–10PM","10PM–2AM"]
    sched=user.get("schedule",{})
    grid=""
    for d in days:
        cells="".join(f'<td style="padding:8px;text-align:center;"><input type="checkbox" {"checked" if sched.get(d,{}).get(s) else ""} onchange="toggleSlot(\'{d}\',\'{s}\',this.checked)" style="width:16px;height:16px;accent-color:#C8332A;"></td>' for s in slots)
        grid+=f'<tr><td style="padding:10px 14px;font-size:13px;font-weight:600;white-space:nowrap;">{d}</td>{cells}</tr>'
    headers="".join(f'<th style="padding:10px 8px;font-size:10px;letter-spacing:1px;color:var(--muted);text-transform:uppercase;text-align:center;">{s}</th>' for s in slots)
    body=f"""{sidebar_html("schedule",user)}
<div class="mc">
<div class="topbar"><div><h1>📅 My Schedule</h1><p>Set your weekly availability (all times EST)</p></div>
<button class="btn bp" onclick="saveSchedule()">Save Schedule</button></div>
<div class="card fi fi1">
  <p style="font-size:13px;color:var(--muted);margin-bottom:16px;line-height:1.7;">Select the time slots when you are available to work each week. Clients will use this to schedule your moderation shifts. All times are Eastern Standard Time (EST).</p>
  <div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;">
    <thead><tr><th style="text-align:left;padding:10px 14px;font-size:10px;letter-spacing:1px;color:var(--muted);text-transform:uppercase;">Day</th>{headers}</tr></thead>
    <tbody id="schedgrid">{grid}</tbody>
  </table></div>
</div>
</div>"""
    return page("My Schedule",f'<div class="layout">{body}</div>',"""<script>
let schedule={};
document.querySelectorAll('input[type=checkbox]').forEach(cb=>{
  const row=cb.closest('tr').querySelector('td').textContent.trim();
  if(!schedule[row])schedule[row]={};
});
function toggleSlot(day,slot,val){if(!schedule[day])schedule[day]={};schedule[day][slot]=val;}
async function saveSchedule(){
  const r=await fetch('/save_schedule',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({schedule})});
  const d=await r.json();if(d.success)toast('Schedule saved!','s');else toast('Error saving.','e');
}
</script>""")

# ── TRAINING PAGE ─────────────────────────────────────────────
def training_pg(user):
    completed=user.get("completed_courses",[])
    cards=""
    for c in COURSES:
        done=c["id"] in completed
        lk=" style='opacity:0.5;pointer-events:none;'" if c["locked"] else ""
        cards+=f'''<div class="card fi fi{(c["id"]%5)+1}"{lk}>
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
  <span style="font-size:28px;">{c["icon"]}</span>
  {"<span class='bdg b-green'>✅ Completed</span>" if done else ("<span class='bdg b-grey'>🔒 Locked</span>" if c["locked"] else "<span class='bdg b-blue'>Available</span>")}
</div>
<div style="font-size:14px;font-weight:700;margin-bottom:4px;">{c["title"]}</div>
<div style="font-size:11px;color:var(--muted);margin-bottom:8px;">{c["level"]} · {c["dur"]}</div>
<div style="font-size:12px;color:var(--muted);line-height:1.7;margin-bottom:14px;">{c["desc"]}</div>
{"<a href='/training?c="+str(c["id"])+"' class='btn bp bsm' style='width:100%;justify-content:center;'>"+("Review Course" if done else "Start Course →")+"</a>" if not c["locked"] else "<button class='btn bl bsm' style='width:100%;' disabled>🔒 Locked</button>"}
</div>'''
    body=f"""{sidebar_html("training",user)}
<div class="mc">
<div class="topbar"><div><h1>📚 Training Center</h1><p>Earn certifications and unlock higher-paying positions</p></div>
<span class="bdg b-green">{len(completed)}/{len(COURSES)} Completed</span></div>
<div class="g3">{cards}</div>
</div>"""
    return page("Training",f'<div class="layout">{body}</div>')

def course_pg(user, cid, lid):
    c=next((x for x in COURSES if x["id"]==cid),None)
    if not c or not c["lessons"]: return redirect("/training")
    lessons=c["lessons"]
    total=len(lessons)
    lid=max(0,min(lid,total-1))
    title,content=lessons[lid]
    is_last=lid==total-1
    nav=""
    if lid>0: nav+=f'<a href="/training?c={cid}&l={lid-1}" class="btn bo">← Previous</a>'
    if not is_last: nav+=f'<a href="/training?c={cid}&l={lid+1}" class="btn bp">Next Lesson →</a>'
    else: nav+=f'<button class="btn bp" onclick="completeCourse({cid})">🎓 Complete & Earn Certificate →</button>'
    lesson_list="".join(f'<a href="/training?c={cid}&l={i}" style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;font-size:12px;font-weight:{"700" if i==lid else "500"};color:{"var(--red)" if i==lid else "var(--muted)"};background:{"var(--red-light)" if i==lid else "transparent"};margin-bottom:3px;"><span style="width:20px;height:20px;border-radius:50%;background:{"var(--red)" if i==lid else "var(--bdr)"};display:flex;align-items:center;justify-content:center;font-size:9px;color:{"#fff" if i==lid else "var(--muted)"};font-weight:700;flex-shrink:0;">{i+1}</span>{t}</a>' for i,(t,_) in enumerate(lessons))
    body=f"""{sidebar_html("training",user)}
<div class="mc">
<div class="topbar"><div><h1>{c["icon"]} {c["title"]}</h1><p>Lesson {lid+1} of {total} · {c["level"]}</p></div>
<a href="/training" class="btn bo bsm">← Back to Courses</a></div>
<div class="g2">
  <div style="grid-column:1;">
    <div class="card" style="margin-bottom:16px;"><div style="font-size:12px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">Course Lessons</div>{lesson_list}</div>
    <div class="card"><div class="pb"><div class="pf" style="width:{int((lid+1)/total*100)}%"></div></div><div style="font-size:11px;color:var(--muted);margin-top:8px;">Lesson {lid+1} of {total}</div></div>
  </div>
  <div>
    <div class="card">
      <div style="font-size:16px;font-weight:800;margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid var(--bdr);">{title}</div>
      <div style="font-size:13px;line-height:2;color:var(--text);white-space:pre-line;">{content}</div>
      <div style="display:flex;gap:10px;margin-top:22px;padding-top:14px;border-top:1px solid var(--bdr);">{nav}</div>
    </div>
  </div>
</div>
</div>"""
    return page(title,f'<div class="layout">{body}</div>',f"""<script>
async function completeCourse(cid){{
  const r=await fetch('/complete_course',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{course_id:cid}})}});
  const d=await r.json();if(d.success){{toast('🎓 Certificate earned!','s');setTimeout(()=>window.location='/training',1500);}}
}}
</script>""")

# ── LIVE CHAT ─────────────────────────────────────────────────
def livechat_pg(user):
    chats=get_chats(user.get("email",""))
    msgs=""
    if not chats:
        msgs='<div class="cmsg sup"><div>👋 Hi there! I\'m your Moderation Squad support agent. How can I help you today?</div><div class="mt">Just now</div></div>'
    else:
        msgs="".join(f'<div class="cmsg {c["role"]}"><div>{c["msg"]}</div><div class="mt">{c["time"]}</div></div>' for c in chats)
    body=f"""{sidebar_html("livechat",user)}
<div class="mc">
<div class="topbar"><div><h1>💬 Live Support Chat</h1><p>Get help from our support team</p></div><span class="bdg b-green">● Online</span></div>
<div class="g2">
  <div class="chat-wrap" style="grid-column:1/-1;max-width:700px;">
    <div class="chat-hdr">
      <div style="width:36px;height:36px;border-radius:50%;background:var(--red);display:flex;align-items:center;justify-content:center;font-size:16px;">🛡️</div>
      <div><div style="font-size:13px;font-weight:700;">ModSquad Support</div><div style="font-size:11px;color:var(--ok);">● Online · Typically replies in minutes</div></div>
    </div>
    <div class="chat-msgs" id="msgs">{msgs}</div>
    <div class="chat-inp">
      <textarea class="cinput" id="inp" rows="1" placeholder="Type your message..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){{event.preventDefault();send();}}"></textarea>
      <button class="btn bp" onclick="send()">Send</button>
    </div>
  </div>
</div>
</div>"""
    return page("Live Support",f'<div class="layout">{body}</div>',"""<script>
const msgs=document.getElementById('msgs');msgs.scrollTop=msgs.scrollHeight;
async function send(){
  const inp=document.getElementById('inp');const msg=inp.value.trim();if(!msg)return;
  inp.value='';
  msgs.innerHTML+=`<div class="cmsg usr"><div>${{msg}}</div><div class="mt">Just now</div></div>`;
  msgs.scrollTop=msgs.scrollHeight;
  const r=await fetch('/chat_msg',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({msg})});
  const d=await r.json();
  if(d.success){msgs.innerHTML+=`<div class="cmsg sup"><div>${{d.reply}}</div><div class="mt">${{d.time}}</div></div>`;msgs.scrollTop=msgs.scrollHeight;}
}
</script>""")

# ── SUPPORT PAGE ──────────────────────────────────────────────
def support_pg(user):
    faqs=[
        ("How do I get my first job?","Browse the Jobs section and apply for any Newcomer-level position. You will receive an email confirmation within 1-3 business days. Complete 6 jobs to unlock Junior level."),
        ("When do I get paid?","Payouts process every Friday for the prior week's work. Minimum payout is $10. Set up your payment method in the Earnings section first."),
        ("How do I level up?","Newcomer → Junior requires 6 completed jobs. Junior → Senior requires 21 jobs. Senior → Elite requires 50 jobs. Each level unlocks higher-paying positions."),
        ("Is my payment information secure?","Yes. All payment data is encrypted with bank-level security. We support Direct Deposit, PayPal, Payoneer, Tipalti, and Paper Check."),
        ("Can I work part-time?","Absolutely. Set your availability in My Schedule. You can work as few as 8 hours per week for Newcomer positions up to 40 hours/week at Elite level."),
        ("What if I have a problem with a client?","Use the Live Support Chat or email support@moderationsquad.com. Our team responds Mon-Fri 9AM-6PM EST within 4 hours."),
    ]
    faq_html="".join(f'<div class="faq-item"><div class="faq-q">{q} <span class="faq-arr">▼</span></div><div class="faq-a">{a}</div></div>' for q,a in faqs)
    body=f"""{sidebar_html("support",user)}
<div class="mc">
<div class="topbar"><div><h1>❓ Help & FAQ</h1><p>Find answers to common questions</p></div></div>
<div class="g2 fi fi1">
  <div>
    <div class="card" style="margin-bottom:16px;"><div class="sh"><h2>Frequently Asked Questions</h2></div>{faq_html}</div>
  </div>
  <div class="card" style="height:fit-content;">
    <div class="sh"><h2>Contact Support</h2></div>
    <div style="display:flex;flex-direction:column;gap:12px;">
      <div style="background:var(--bg);border-radius:10px;padding:14px;border:1px solid var(--bdr);"><div style="font-size:12px;font-weight:700;">📧 Email Support</div><div style="font-size:12px;color:var(--muted);margin-top:3px;">{S_EMAIL}</div><div style="font-size:11px;color:var(--muted);margin-top:2px;">Response within 4 hours, Mon-Fri</div></div>
      <div style="background:var(--bg);border-radius:10px;padding:14px;border:1px solid var(--bdr);"><div style="font-size:12px;font-weight:700;">📱 Phone Support</div><div style="font-size:12px;color:var(--muted);margin-top:3px;">{S_PHONE}</div><div style="font-size:11px;color:var(--muted);margin-top:2px;">Mon-Fri 9AM-6PM EST</div></div>
      <a href="/livechat" class="btn bp" style="justify-content:center;">💬 Start Live Chat →</a>
    </div>
  </div>
</div>
</div>"""
    return page("Help & FAQ",f'<div class="layout">{body}</div>')

# ── ROUTES ────────────────────────────────────────────────────
@app.route("/")
def index(): return landing()

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        data=request.json or {}
        email=data.get("email","").strip().lower()
        if email not in [e.lower() for e in WHITELIST]:
            return jsonify({"success":False,"message":"⛔ Access Denied. Your email is not on our approved list."})
        otp=str(random.randint(100000,999999))
        set_otp(email, otp)
        threading.Thread(target=send_otp,args=(email,otp)).start()
        return jsonify({"success":True})
    return login_pg()

@app.route("/verify", methods=["POST"])
def verify():
    data=request.json or {}
    email=data.get("email","").strip().lower()
    code=data.get("code","").strip()
    if check_otp(email, code):
        session["user"]=email
        user=get_user(email)
        if not user:
            name=email.split("@")[0].replace("."," ").replace("_"," ").title()
            user={
                "email":email,"name":name,"level":"Newcomer","jobs_done":0,
                "earned":0.0,"member_since":datetime.now().strftime("%b %Y"),
                "avatar":None,"applied_jobs":[],
                "verifications":{"email":True,"residence":True,"id":True,"tax":True,"payment":False,"background":True},
                "schedule":{},"completed_courses":[]
            }
            save_user(user)
            add_notif(email,f"🎉 Welcome to Moderation Squad, {name}! Your account is verified and ready.")
        return jsonify({"success":True})
    return jsonify({"success":False,"message":"❌ Invalid or expired code. Please try again."})

@app.route("/dashboard")
def dashboard():
    if "user" not in session: return redirect("/login")
    return dash_pg(get_user(session["user"]))

@app.route("/jobs")
def jobs():
    if "user" not in session: return redirect("/login")
    pg=int(request.args.get("pg",1))
    return jobs_pg(get_user(session["user"]),pg)

@app.route("/profile")
def profile():
    if "user" not in session: return redirect("/login")
    return profile_pg(get_user(session["user"]))

@app.route("/earnings")
def earnings():
    if "user" not in session: return redirect("/login")
    return earnings_pg(get_user(session["user"]))

@app.route("/notifications")
def notifications():
    if "user" not in session: return redirect("/login")
    return notif_pg(get_user(session["user"]))

@app.route("/schedule")
def schedule():
    if "user" not in session: return redirect("/login")
    return schedule_pg(get_user(session["user"]))

@app.route("/training")
def training():
    if "user" not in session: return redirect("/login")
    cid=request.args.get("c")
    lid=int(request.args.get("l","0"))
    user=get_user(session["user"])
    if cid is not None: return course_pg(user,int(cid),lid)
    return training_pg(user)

@app.route("/livechat")
def livechat():
    if "user" not in session: return redirect("/login")
    return livechat_pg(get_user(session["user"]))

@app.route("/support")
def support():
    if "user" not in session: return redirect("/login")
    return support_pg(get_user(session["user"]))

@app.route("/apply_job", methods=["POST"])
def apply_job():
    if "user" not in session: return jsonify({"success":False})
    data=request.json or {}
    email=session["user"]
    user=get_user(email)
    t,c,p=data.get("title",""),data.get("company",""),data.get("pay","")
    days=random.randint(1,3)
    applied=user.get("applied_jobs",[])
    applied.append({"title":t,"company":c,"pay":p,"status":"Under Review","date":datetime.now().strftime("%b %d, %Y"),"days":days})
    user["applied_jobs"]=applied
    save_user(user)
    add_notif(email,f"✅ Applied for {t} at {c}. Response expected within {days} business day{'s' if days>1 else ''}.")
    threading.Thread(target=send_app_email,args=(email,user.get("name","Moderator"),t,c,p,days)).start()
    return jsonify({"success":True,"days":days})

@app.route("/upload_avatar", methods=["POST"])
def upload_avatar():
    if "user" not in session: return jsonify({"success":False})
    img=(request.json or {}).get("image","")
    email=session["user"]
    user=get_user(email)
    if user:
        user["avatar"]=img
        save_user(user)
        add_notif(email,"📸 Profile picture updated successfully!")
    return jsonify({"success":True})

@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "user" not in session: return jsonify({"success":False})
    data=request.json or {}
    email=session["user"]
    user=get_user(email)
    if user and data.get("name"):
        user["name"]=data["name"]
        save_user(user)
        add_notif(email,"👤 Profile name updated.")
    return jsonify({"success":True})

@app.route("/save_schedule", methods=["POST"])
def save_schedule():
    if "user" not in session: return jsonify({"success":False})
    data=request.json or {}
    email=session["user"]
    user=get_user(email)
    if user:
        user["schedule"]=data.get("schedule",{})
        save_user(user)
        add_notif(email,"📅 Schedule updated successfully!")
    return jsonify({"success":True})

@app.route("/complete_course", methods=["POST"])
def complete_course():
    if "user" not in session: return jsonify({"success":False})
    data=request.json or {}
    email=session["user"]
    user=get_user(email)
    cid=data.get("course_id")
    if user and cid is not None:
        completed=user.get("completed_courses",[])
        if cid not in completed:
            completed.append(cid)
            user["completed_courses"]=completed
            course=next((c for c in COURSES if c["id"]==cid),None)
            save_user(user)
            if course: add_notif(email,f"🎓 Certificate earned: {course['title']}!")
    return jsonify({"success":True})

@app.route("/chat_msg", methods=["POST"])
def chat_msg():
    if "user" not in session: return jsonify({"success":False})
    data=request.json or {}
    email=session["user"]
    msg=data.get("msg","").strip()
    if not msg: return jsonify({"success":False})
    add_chat(email,"usr",msg)
    ml=msg.lower()
    kb={"pay":"Our Newcomer pay starts at $5–$6/hr. Level up through Junior ($10–$12), Senior ($13–$18), and Elite ($18–$22/hr). Payouts every Friday!",
        "payment":"We support Direct Deposit (ACH), PayPal, Payoneer, Tipalti, and Paper Check. Set up your method in the Earnings section.",
        "job":"You have 3 open Newcomer positions! Browse Jobs and click Apply Now. Complete 6 jobs to unlock Junior level with better pay.",
        "verify":"Your profile is almost fully verified! The only remaining step is setting up your Payment Method in Earnings.",
        "level":"Complete 6 jobs → Junior, 21 jobs → Senior, 50 jobs → Elite. Each level unlocks better-paying positions!",
        "train":"Training Center has 3 free beginner courses: Chat Moderation Fundamentals, Content Policy, and Effective Communication. Click Training in the sidebar!",
        "schedule":"Set your weekly availability in My Schedule. Pick days and time slots (EST) and clients will schedule you accordingly.",
        "payout":"Payouts process every Friday for the prior week. Minimum $10. Make sure your payment method is set up in Earnings first.",
        "hello":"Hi there! 👋 I'm your Moderation Squad support agent. How can I help you today?",
        "hi":"Hello! 👋 I'm here to help! Ask me about pay, jobs, verification, training, scheduling, or anything else.",
        "help":"Happy to help! I can answer questions about: pay rates, job applications, profile verification, training courses, scheduling, and account issues. What do you need?"}
    reply="Thanks for reaching out! I can help with pay rates, job applications, verification, training, scheduling, and more. What specifically do you need?"
    for k,v in kb.items():
        if k in ml: reply=v; break
    t=add_chat(email,"sup",reply)
    return jsonify({"success":True,"reply":reply,"time":t})

@app.route("/ping")
def ping(): return "ok"

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=False)
