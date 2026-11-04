# NIXYZ Privacy Policy

Version 1.0, effective November 5, 2026. Applies to NIXYZ version 2.0.0 and later.

## 1. In short

The author of NIXYZ does not receive your data. The program has no accounts, telemetry, analytics or ads, and the author has no servers of their own. Everything the program stores stays on your computer.

However, the program connects to third-party services, and they can see those connections, including your IP address. See section 4.

## 2. Who is responsible for the program

The author of NIXYZ, GitHub: Yonswi. Contact: https://github.com/Yonswi/NIXYZ/issues

Since the author does not receive your data through the program, the author cannot view, share or delete it for you: you can delete it yourself (section 6).

## 3. What is stored on your computer

In the C:\Program Files\NIXYZ\data folder:

- settings: language, theme, selected strategy, enabled modes and your own DNS server, if you entered one;
- zapret engine files and their checksums;
- your lists of sites and addresses, if you filled them in;
- your previous network settings (adapter DNS, Wi-Fi mode, TCP auto-tuning), so they can be restored;
- the result of the last speed test.

The activity log is kept only in memory and disappears when the program closes. The engine runs without writing a log file. The program window runs in private mode: its service files are in a temporary folder and are deleted on closing.

The engine processes network packets on your computer and sends them nowhere other than the connection's normal destination.

Files appear outside this folder only when you press a button: Support report and Export settings save a file to your Downloads folder. The program does not send them anywhere by itself. The report hides your user name, computer name, network addresses and the sites you checked, but review it yourself before sending it to anyone. These files stay in Downloads after the program is removed.

## 4. What the program connects to

With any connection, the service can see your IP address, the time of the request and technical connection data. These services work under their own privacy policies, and the author does not control them.

Always:

- GitHub (github.com, api.github.com and file download servers): checking for updates at startup and downloading the engine. Here the program identifies itself as NIXYZ with its version number.

When checking access (after turning the bypass on, by button, while picking a strategy, and in the background Watchdog and Re-check at night, if you turned them on):

- YouTube and Google (www.youtube.com, i.ytimg.com, redirector.googlevideo.com);
- Discord (discord.com, gateway.discord.gg, cdn.discordapp.com);
- Cloudflare (www.cloudflare.com, speed.cloudflare.com, cdnjs.cloudflare.com);
- ChatGPT, Claude and Grok (chatgpt.com, claude.ai, grok.com): a request for a service page, to learn which country the service sees you in. These requests happen even if you do not use these services.

Only on your action:

- a site you check in the lists section;
- the Boost screen: the DNS servers of Cloudflare, Google and Quad9, to measure latency. If you select one of them, all of the computer's DNS queries go to that provider;
- the Test speed button: speed.cloudflare.com, yandex.ru/internet and *.yandex.net servers, speedtest.selectel.ru.

Only if you turned Smart route on:

- dns.comss.one and the fallback geohide.ru, or a server you entered. It receives DNS queries for the listed AI services and your IP address, and connections to these services go through its proxies. The content stays encrypted, but the owner of the server can see when and from where you access them.

In addition, your provider may see your computer's connections: NIXYZ does not encrypt traffic or hide your IP address.

## 5. Windows components and contacting the author

The program window uses Microsoft Edge WebView2. It and Windows itself may exchange data with Microsoft according to your system settings and Microsoft's policy.

If you write to the author on GitHub, your message and profile are publicly visible and handled by GitHub. Do not post personal data there. Messages in Issues are visible to everyone.

## 6. Managing and deleting your data

- Put everything back returns the changed network settings.
- Removing the program deletes the data folder with all settings and the engine.
- Delete report and export files in Downloads yourself.
- Request data held by third-party services from those services.

## 7. Children

The program is not designed to collect data about children and does not ask for the user's age, name or contact details.

## 8. Changes to this policy

If the program starts handling data differently, a new edition will be published in the repository together with that version of the program. The author will not add telemetry without stating it explicitly in this document.
