# NIXYZ Terms of Use

Version 1.0, effective November 5, 2026. Applies to NIXYZ version 2.0.0 and later.

## 1. About this document

This is an agreement between you and the author of NIXYZ (GitHub: Yonswi, the "author"). By installing or using the program, you confirm that you have read and accept it. If you do not agree, do not install the program, and remove it if it is installed.

If you are under 18, use the program only with the consent of a parent or legal guardian.

## 2. What NIXYZ is

NIXYZ is a free, open-source program for Windows. It is a shell for the third-party zapret engine: it downloads, configures and runs it on your computer. The program is intended for diagnosing and restoring network connections on your device.

NIXYZ is not a communications service, a VPN or a paid service. The author does not operate servers that carry your traffic, does not sell the program and does not provide access to any content.

## 3. Licenses

The NIXYZ code is distributed under the MIT License (the LICENSE file). Third-party components, including zapret, WinDivert and zapret-discord-youtube, belong to their authors and have their own licenses (the THIRD_PARTY_NOTICES.md file).

These terms do not limit the rights to the code granted by the MIT License. If they differ regarding rights to the code, the license prevails.

## 4. What the program does on your computer

By installing NIXYZ, you agree that the program:

- runs with administrator rights;
- on first launch, downloads the zapret engine from GitHub by itself, picks a setting and turns the bypass on;
- runs the WinDivert driver, which intercepts and modifies network packets on this computer;
- may enable the TCP timestamps setting in Windows, which the engine needs;
- only on your action, changes DNS, Wi-Fi power mode and TCP auto-tuning, and adds a DNS rule for Smart route and an autostart task.

The program remembers your previous network settings and tries to restore them when you restore settings or remove it. This cannot be guaranteed in all conditions.

Antivirus software may react to the engine and driver, and Windows may warn about an unknown publisher: the installer is not signed.

## 5. Your responsibility and lawful use

Laws on network restrictions and tools for bypassing them differ by country and change over time. You alone are responsible for making sure your use of the program complies with the laws of your country and of the place where you are. If using the program is prohibited where you are, do not use it.

You agree:

- not to use the program to break the law, including to access or distribute prohibited material;
- not to use it for attacks, fraud, violating the rights of others or bypassing the security of other people's systems;
- to follow the terms of the services you connect to;
- not to use the program on someone else's or a work network without its owner's permission.

The author does not encourage bypassing restrictions established by law and does not assess what is permitted in your particular case. These terms are not legal advice.

## 6. NIXYZ provides no anonymity or protection

The program does not hide your IP address or encrypt your traffic. Your provider and the services you visit may see your connections. Do not rely on NIXYZ where anonymity or security matter.

## 7. Third-party services and Smart route

The program connects to third-party services listed in the Privacy Policy. The author does not control them and is not responsible for their operation, content or handling of your data.

Smart route is off by default. If you turn it on, DNS queries for the listed AI services go to a third-party DNS server, and connections to them go through its proxies. The content stays encrypted, but the owner of that server can see when and from where you access those services. The author does not verify or control this server.

The terms of some services restrict use from unsupported countries. A service may restrict or block your account. You accept this risk. Read the terms of the services themselves, for example:

- OpenAI: https://help.openai.com/en/articles/9131992-chatgpt-and-api-services-in-unsupported-countries-and-territories
- Anthropic: https://www.anthropic.com/supported-countries

The program shows a hint about this the first time Smart route is turned on.

## 8. No warranty

The program is provided free of charge and "as is". The author does not guarantee that it will suit your purposes, work without errors, open any particular service or be compatible with your hardware, provider and other programs. The engine may stop working because of actions by providers, services or the engine's authors.

Before using programs that change network settings, take care of your important data and of your ability to restore the system.

## 9. Limitation of liability

To the maximum extent permitted by applicable law, the author is not liable for any direct or indirect damages related to using or being unable to use the program. This includes data loss, network or system failures, blocked accounts, and the consequences of your violating laws or the terms of third-party services.

This section does not limit liability or consumer rights that cannot be limited or excluded under applicable law.

## 10. Updates and ending use

The program offers engine updates by itself and installs them with your consent. Updates of NIXYZ itself are published in the repository. The author may change or stop developing the program at any time.

You may stop using the program at any time by removing it in its settings or in Windows Settings → Apps. If you breach these terms, your right to use the program under them ends, but this does not cancel the rights to the code under the MIT License.

## 11. Changes to these terms

A new edition is published in the program's repository and applies to NIXYZ versions released with it or later. If you do not agree with a new edition, do not install those versions.

## 12. Final provisions

These terms do not choose the law of any particular country. They are governed by the law determined under the rules of private international law, and this does not deprive you of consumer rights that are mandatory in your country of residence. The parties first try to resolve any dispute by correspondence. If any provision is found invalid, the rest remain in force. The main text is Russian; the English text is provided for convenience.

## 13. Contact

Questions and comments: https://github.com/Yonswi/NIXYZ/issues
