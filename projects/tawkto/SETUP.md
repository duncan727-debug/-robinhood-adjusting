# Tawk.to live chat — setup

## Why Tawk.to over Crisp / Intercom
- **Free forever**, not a trial. No agent-count limit. No message cap.
- iOS/Android apps so you can answer from your phone.
- API access for me to read/reply to chats programmatically.

## What I need from Duncan (3 min)
1. Go to **https://www.tawk.to/** → "Sign Up Free".
2. Use `duncanlittlejohn727@gmail.com`.
3. When asked for property name: **Robinhood Adjusting**. URL: **https://robinhoodadjusting.com**.
4. After signup, install the iOS app (search "Tawk.to") + log in.
5. From the dashboard: **Administration → Channels → Chat Widget → JavaScript installation**. Copy the snippet — it looks like:
   ```html
   <!--Start of Tawk.to Script-->
   <script type="text/javascript">
   var Tawk_API=Tawk_API||{}, Tawk_LoadStart=new Date();
   (function(){
   var s1=document.createElement("script"),s0=document.getElementsByTagName("script")[0];
   s1.async=true;
   s1.src='https://embed.tawk.to/XXXXXXX/YYYYYY';
   ...
   })();
   </script>
   <!--End of Tawk.to Script-->
   ```
6. Paste it into `config/.secrets` like:
   ```
   TAWKTO_PROPERTY_ID=XXXXXXX
   TAWKTO_WIDGET_ID=YYYYYY
   ```

## What I do (after you hand over the IDs)
1. Inject the script into `site/index.html`, `site/PA-WEBSITE.html`, and all generated brief/trends pages.
2. Set the off-hours auto-response: "We're away. Leave your name, mobile, and a sentence about your situation — Duncan will get back to you within 1 hour during business hours."
3. Configure the pre-chat form (name + mobile + reason for visit).
4. Wire Tawk.to webhook → HubSpot contact creation (new chat = new lead).
5. Set up "Robin" as a chat agent persona (same intake script as the phone agent) so when you're away, the chat still qualifies the visitor.

## Cost
- $0/mo forever (free tier).
- Optional paid add-on later: "Remove Tawk.to branding" ~$19/mo. Skip for now.

## Risk
- If we don't reply within 5-10 min during business hours, visitors bounce. Worse than no chat.
- Mitigation: the iOS app pings you. If you can't answer in time, the auto-response captures contact info so the lead isn't lost.
