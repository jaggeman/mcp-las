// ---------------------------------------------------------
    // Multilingual Translations Dictionary (SV / EN)
    // ---------------------------------------------------------
    const TRANSLATIONS = {
      sv: {
        country_SE_title: "🇸🇪 Sverige (SE)",
        country_SE_desc: "11 lagar, inklusive LAS, MBL, Semesterlagen och Kvittningslagen. Svenska beräkningar, kollektivavtal och AD-prejudikat.",
        country_DK_title: "🇩🇰 Danmark (DK)",
        country_DK_desc: "Avgränsad arbetsrättskatalog från Beskæftigelsesministeriet och Retsinformation, synkad varje vecka.",
        country_FI_title: "🇫🇮 Finland (FI)",
        country_FI_desc: "Åtta centrala arbetsrättslagar från Finlex, synkade varje vecka.",
        country_NO_title: "🇳🇴 Norge (NO)",
        country_NO_desc: "9 lagar: även permitteringslön, lönegaranti och arbetsskadeförsäkring.",
        country_DE_title: "🇩🇪 Tyskland (DE)",
        country_DE_desc: "11 lagar: även MuSchG, BEEG och NachwG — moderskapsskydd, föräldraledighet och anställningsvillkor.",
        country_ES_title: "🇪🇸 Spanien (ES)",
        country_ES_desc: "7 lagar: anställning, arbetsmiljö, facklig frihet, jämställdhet, distansarbete, sysselsättning och arbetsinspektion.",
        country_NL_title: "🇳🇱 Nederländerna (NL)",
        country_NL_desc: "9 centrala arbetsrättslagar från det officiella Basiswettenbestand.",
        country_GB_title: "🇬🇧 Storbritannien (GB)",
        country_GB_desc: "10 centrala arbetsrättslagar och förordningar från officiell Akoma Ntoso XML. Employment Rights Act omfattar sections 1–145.",
        spanish_scope: "Spanien: konsoliderade BOE-texter är informativa. Bilagor och kompletterande/övergångsbestämmelser ingår inte i artikelindexet. Kontrollera originalpubliceringen vid rättsliga beslut.",

        status_live: "FastMCP • Live",
        nav_connect: "Anslut AI",
        nav_sources: "Källor & Data",
        nav_tools: "Verktyg",
        nav_api: "REST API",
        nav_connect_btn: "Anslut direkt",
        hero_badge: "Arbetsrätt från officiella källor · 8 länder",
        hero_title_1: "Europeisk arbetsrätt",
        hero_title_2: "direkt till din AI-Agent",
        hero_sub: "Laguppslag och sökning i åtta europeiska länder på källspråket. Avgränsade lagkataloger – inte fullständig nationell arbetsrätt. Beräkningar, kollektivavtal, AD-prejudikat och HR-mallar gäller endast Sverige.",
        hero_btn_connect: "Anslut direkt till din AI",
        hero_btn_request: "Begär dedikerad åtkomst",
        conn_title: "Anslut till din AI (Claude, ChatGPT, Gemini, Cursor)",
        conn_badge: "Modern Streamable HTTP • Live på Cloud Run",
        conn_sub: "Välj din AI-plattform nedan för att få färdig URL, konfigurationskod och installationsprompt:",
        claude_url_title: "1. Streamable HTTP URL (för Custom Connector)",
        claude_config_title: "2. Konfiguration för Claude Desktop (claude_desktop_config.json)",
        gpt_url_title: "1. MCP-koppling för ChatGPT Desktop / OpenAI Developer Mode",
        gpt_url_desc: "Använd denna Streamable HTTP-adress direkt i ChatGPT Desktop:",
        gpt_prompt_title: "2. System Prompt för Custom GPTs",
        gpt_prompt_desc: "Klistra in denna instruktion i din Custom GPT:",
        gemini_prompt_title: "1. Prompt för Google Gemini (Gems & Agenter)",
        gemini_prompt_desc: "Klistra in denna instruktion i din Gemini Gem eller AI Studio Agent:",
        cursor_config_title: "1. Cursor / Windsurf MCP-konfiguration (.cursor/mcp.json)",
        btn_copy_url: "Kopiera URL",
        btn_copy_json: "Kopiera JSON",
        btn_copy_prompt: "Kopiera Prompt",
        sources_title: "Lagkällor & indexering",
        sources_sub: "Strukturerad juridisk kunskapsbas indexerad i Google Firestore",
        sync_title: "Automatisk källsynkronisering & Multi-Jurisdiktion",
        sync_desc: "Veckovis synk av åtta länder. Sverige hämtas på GitHub-runnern och övriga via Cloud Run Job i Frankfurt. Ändrade texter versionskontrolleras före indexering. Välj jurisdiction: SE, DK, FI, NO, DE, ES, NL eller GB.",
        sync_note: "Alla åtta landkataloger är indexerade. Aktuell mängd och senaste synk visas live från get_legal_coverage.",
        danish_title: "Europeiska lagar och officiella källor",
        danish_desc: "Källspråk: svenska, danska, finska, norska bokmål, tyska, spanska, nederländska och engelska. Sök på källspråket; översättning garanteras inte. Länderna hålls åtskilda. Ingen utländsk praxis, kollektivavtalstolkning eller HR-beräkning utlovas.",
        src_card1_title: "Sveriges Riksdag",
        src_card1_desc: "Fulltext-indexerade lagar med paragrafindelat innehåll: LAS (1982:80), MBL (1976:580), Semesterlagen (1977:480), Arbetstidslagen m.fl.",
        src_card2_title: "17 Kollektivavtal",
        src_card2_desc: "Kurerade avtalsregler för Teknikavtalet, Almega IT, Detaljhandeln, SKR AB, Statliga Villkorsavtal m.fl. som hanterar semidispositivitet.",
        src_card3_title: "Arbetsdomstolen (60 AD-Domar)",
        src_card3_desc: "60 vägledande domar och prejudikat: sakliga skäl (nya LAS 2022), personliga skäl, arbetsbrist, hyvling 7 b §, treundantaget 22 §, lojalitetsplikt, 29/29-principen m.fl.",
        src_card4_title: "Sveriges Riksbank",
        src_card4_desc: "Officiell kalender för bankdagar och helgdagar 2026 för beräkning av löneutbetalningar och lagstadgade frister (Lag 1930:173).",
        src_card5_title: "Försäkringskassan & SGI",
        src_card5_desc: "Rehabiliteringsplan (30 kap. 6 § SFB, FK 7459), sjukpenningtak (10 PBB) och samverkan vid nedsatt arbetsförmåga.",
        src_card6_title: "SCB & Skatteverket",
        src_card6_desc: "Officiella prisbasbelopp (57 300 kr 2024 / 58 800 kr 2025), inkomstbasbelopp och skattefria schabloner (milersättning 25 kr/mil, traktamente 290 kr).",
        src_card7_title: "Danmark (Retsinformation.dk)",
        src_card7_desc: "Avgränsad arbetsrättskatalog från Beskæftigelsesministeriet och Retsinformation, synkad varje vecka.",
        src_card8_title: "Finland (Finlex.fi)",
        src_card8_desc: "Åtta centrala arbetsrättslagar från Finlex, synkade varje vecka.",
        badge_synced: "Senast synkad:",
        badge_updated: "Senast uppdaterad:",
        badge_source: "Källa:",
        badge_calendar: "Officiell kalender:",
        badge_jurisdiction: "Jurisdiktion:",
        tools_title: "Vad du kan fråga din AI",
        tools_sub: "Dessa 19 intelligenta verktyg anropas automatiskt i bakgrunden via MCP för AI-agenter och Claude",
        tip_heading: "💡 AI-Tips:",
        tip_text1: "Du behöver inte memorera verktygen! När du är ansluten i Claude, ChatGPT eller Cursor kan du bara fråga din AI:",
        tip_code: '"Vilka verktyg har du tillgång till via MCP LAS?"',
        tip_text2: " eller be den lista alla tillgängliga funktioner direkt i chatten.",
        search_placeholder: "Sök verktyg (t.ex. semester, turordning, excel, LAS 7 §, varsel, basbelopp, reseavdrag)...",
        cat_all: "Alla",
        cat_laws: "Lagar & Paragrafer",
        cat_salary: "Semester & Lön",
        cat_turnorder: "Turordning & Excel",
        cat_templates: "HR-Mallar",
        th_tool: "Funktion & Verktyg",
        th_desc: "Vad verktyget gör",
        th_prompt: "Exempel på prompt för din AI",
        btn_copy: "Kopiera",
        btn_copied: "Kopierat!",
        btn_prev: "Föregående",
        btn_next: "Nästa",
        showing_text: (s, e, t) => `Visar ${s}–${e} av ${t} verktyg`,
        no_tools_found: "Inga verktyg matchade din sökning.",
        disc_title: "Ansvarsfriskrivning (Legal Disclaimer)",
        disc_text1: "Detta är en öppen källkodslösning (Open Source) framtagen i informations- och experimentellt syfte för Model Context Protocol (MCP) och AI-agenter. Informationen som tillhandahålls eller tolkas av AI-modeller via detta verktyg utgör inte juridisk rådgivning och ska under inga omständigheter ersätta rådgivning från behörig jurist, arbetsgivarorganisation eller facklig representant.",
        disc_text2: "Skaparen/utvecklaren tar inget juridiskt eller ekonomiskt ansvar för korrektheten i svaren, tolkningar, eventuella ändringar i lagstiftning/avtal eller beslut som fattas baserat på information från denna tjänst.",
        form_title: "Begär Dedikerad API-nyckel",
        form_sub: "För företag, HR-team och organisationer som vill integrera europeisk arbetsrätt i sina interna AI-system.",
        lbl_name: "Namn",
        lbl_email: "E-postadress",
        lbl_company: "Företag / Organisation",
        lbl_reason: "Användningsområde",
        ph_name: "Anna Andersson",
        ph_email: "anna@foretag.se",
        ph_company: "Företag AB",
        ph_reason: "Beskriv kort vad du planerar att använda MCP-servern till...",
        legal_accept: "Jag accepterar användarvillkoren och bekräftar att jag har tagit del av integritetspolicyn.",
        terms_link: "Användarvillkor",
        privacy_link: "Integritets- och cookiepolicy",
        contact_link: "Kontakt",
        btn_submit: "Skicka ansökan",
        btn_submitting: "Skickar...",
        succ_title: "Tack för din ansökan!",
        succ_desc: "Vi har tagit emot dina uppgifter och återkommer via e-post så snart din dedikerade nyckel har godkänts.",
        footer_copy: "© 2026 MCP LAS — Europeisk arbetsrätt för AI-Agenter. Öppen källkodslösning.",
        footer_disclaimer: "Byggd med Model Context Protocol (FastMCP) på Google Cloud Run & Firebase Firestore.",
        footer_report_bug: "Rapportera en bugg eller önskemål på GitHub"
      },
      en: {
        country_SE_title: "🇸🇪 Sweden (SE)",
        country_SE_desc: "11 statutes, including LAS, MBL, the Annual Leave Act and the Employer's Right of Set-off Act. Swedish calculations, collective agreements and Labour Court cases.",
        country_DK_title: "🇩🇰 Denmark (DK)",
        country_DK_desc: "Bounded labour-law catalogue from the Ministry of Employment and Retsinformation, synchronized weekly.",
        country_FI_title: "🇫🇮 Finland (FI)",
        country_FI_desc: "Eight core employment-law statutes from Finlex, synchronized weekly.",
        country_NO_title: "🇳🇴 Norway (NO)",
        country_NO_desc: "9 statutes, now including layoff pay, wage guarantees and occupational injury insurance.",
        country_DE_title: "🇩🇪 Germany (DE)",
        country_DE_desc: "11 statutes, now including MuSchG, BEEG and NachwG — maternity protection, parental leave and employment terms.",
        country_ES_title: "🇪🇸 Spain (ES)",
        country_ES_desc: "7 statutes: employment, occupational safety, trade union freedom, equality, remote work, employment policy and labour inspection.",
        country_NL_title: "🇳🇱 Netherlands (NL)",
        country_NL_desc: "9 core employment-law statutes from the official Basic Laws Database.",
        country_GB_title: "🇬🇧 United Kingdom (GB)",
        country_GB_desc: "10 core employment statutes and regulations from official Akoma Ntoso XML. The Employment Rights Act covers sections 1–145.",
        spanish_scope: "Spain: consolidated BOE texts are informational. Annexes and supplementary/transitional provisions are not indexed. Consult the original publication for legal decisions.",

        status_live: "FastMCP • Live",
        nav_connect: "Connect AI",
        nav_sources: "Sources & Data",
        nav_tools: "Tools",
        nav_connect_btn: "Connect Now",
        hero_badge: "Labour law from official sources · 8 countries",
        hero_title_1: "European labour law",
        hero_title_2: "directly in your AI Agent",
        hero_sub: "Statute lookup and search for eight European countries in the source language. Bounded catalogues, not complete national labour-law coverage. Calculators, collective agreements, Swedish Labour Court cases and HR templates are Sweden-only.",
        hero_btn_connect: "Connect to your AI",
        hero_btn_request: "Request Dedicated Access",
        conn_title: "Connect to your AI (Claude, ChatGPT, Gemini, Cursor)",
        conn_badge: "Modern Streamable HTTP • Live on Cloud Run",
        conn_sub: "Choose your AI platform below for the ready-to-use URL, configuration code, and system prompt:",
        claude_url_title: "1. Streamable HTTP URL (for Custom Connector)",
        claude_config_title: "2. Configuration for Claude Desktop (claude_desktop_config.json)",
        gpt_url_title: "1. MCP Connection for ChatGPT Desktop / OpenAI Developer Mode",
        gpt_url_desc: "Use this Streamable HTTP URL directly in ChatGPT Desktop:",
        gpt_prompt_title: "2. System Prompt for Custom GPTs",
        gpt_prompt_desc: "Paste this instruction into your Custom GPT:",
        gemini_prompt_title: "1. Prompt for Google Gemini (Gems & Agents)",
        gemini_prompt_desc: "Paste this instruction into your Gemini Gem or AI Studio Agent:",
        cursor_config_title: "1. Cursor / Windsurf MCP Configuration (.cursor/mcp.json)",
        btn_copy_url: "Copy URL",
        btn_copy_json: "Copy JSON",
        btn_copy_prompt: "Copy Prompt",
        sources_title: "Legal sources & indexing",
        sources_sub: "Structured employment law dataset indexed in Google Firestore",
        sync_title: "Automated Source Synchronization & Multi-Jurisdiction",
        sync_desc: "Weekly synchronization of eight countries. Sweden is fetched on the GitHub runner and the others by a Cloud Run Job in Frankfurt. Changed texts are version-checked before indexing. Select jurisdiction: SE, DK, FI, NO, DE, ES, NL or GB.",
        sync_note: "All eight country catalogues are indexed. Current counts and the latest synchronization are shown live by get_legal_coverage.",
        danish_title: "European legislation and official sources",
        danish_desc: "Source languages: Swedish, Danish, Finnish, Norwegian Bokmål, German, Spanish, Dutch and English. Search in the source language; translation is not guaranteed. Jurisdictions remain separate. Foreign case law, collective-agreement interpretation and HR calculations are not included.",
        src_card1_title: "Swedish Parliament (Riksdagen)",
        src_card1_desc: "Full-text indexed statutes partitioned by section: Employment Protection Act (LAS 1982:80), Co-Determination Act (MBL 1976:580), Annual Leave Act (1977:480), etc.",
        src_card2_title: "17 Collective Agreements",
        src_card2_desc: "Curated CBA rules for Teknikavtalet, Almega IT, Retail, Municipalities (SKR), State agreements handling semi-dispositive deviations.",
        src_card3_title: "Labour Court (60 AD Precedents)",
        src_card3_desc: "60 authoritative rulings and precedents on objective grounds, personal misconduct, redundancy, 29/29-principle, redeployment, and turnorder.",
        src_card4_title: "Sveriges Riksbank",
        src_card4_desc: "Official calendar for Swedish bank days and public holidays 2026 for salary payout dates and statutory deadlines (Act 1930:173).",
        src_card5_title: "Försäkringskassan & SGI",
        src_card5_desc: "Rehabilitation plans (SFB Chapter 30 Section 6, FK 7459), sickness benefit ceiling (10 PBB), and return-to-work coordination.",
        src_card6_title: "Statistics Sweden & Tax Agency",
        src_card6_desc: "Official price base amounts (2024–2026), income base amounts, and statutory tax-free mileage/per diem deductions.",
        src_card7_title: "Denmark (Retsinformation.dk)",
        src_card7_desc: "Bounded labour-law catalogue from the Ministry of Employment and Retsinformation, synchronized weekly.",
        src_card8_title: "Finland (Finlex.fi)",
        src_card8_desc: "Eight core employment-law statutes from Finlex, synchronized weekly.",
        badge_synced: "Last synced:",
        badge_updated: "Last updated:",
        badge_source: "Source:",
        badge_calendar: "Official calendar:",
        badge_jurisdiction: "Jurisdiction:",
        tools_title: "What you can ask your AI",
        tools_sub: "These 19 intelligent tools are automatically invoked in the background via MCP for AI agents and Claude",
        tip_heading: "💡 AI Tip:",
        tip_text1: "You don't need to memorize the tools! Once connected in Claude, ChatGPT, or Cursor, simply ask your AI:",
        tip_code: '"What tools do you have access to via MCP LAS?"',
        tip_text2: " or ask it to list all available legal capabilities directly in the chat.",
        search_placeholder: "Search tools (e.g. vacation, redundancy, excel, LAS Section 7, notice, travel deduction, base amount)...",
        cat_all: "All",
        cat_laws: "Laws & Statutes",
        cat_salary: "Vacation & Salary",
        cat_turnorder: "Turnorder & Excel",
        cat_templates: "HR Templates",
        th_tool: "Feature & Tool",
        th_desc: "What the tool does",
        th_prompt: "Example Prompt for your AI",
        btn_copy: "Copy",
        btn_copied: "Copied!",
        btn_prev: "Previous",
        btn_next: "Next",
        showing_text: (s, e, t) => `Showing ${s}–${e} of ${t} tools`,
        no_tools_found: "No tools matched your search.",
        disc_title: "Legal Disclaimer",
        disc_text1: "This is an open-source project created for informational and experimental purposes for Model Context Protocol (MCP) and AI agents. Information provided or interpreted by AI models via this tool does not constitute legal advice and must not replace professional advice from a qualified attorney, employers' association, or trade union representative.",
        disc_text2: "The creators/developers accept no legal or financial liability for the accuracy of responses, interpretations, amendments to legislation/agreements, or decisions made based on information from this service.",
        form_title: "Request Dedicated API Key",
        form_sub: "For enterprises, HR teams, and organizations integrating European labour law into internal AI pipelines.",
        lbl_name: "Full Name",
        lbl_email: "Email Address",
        lbl_company: "Company / Organization",
        lbl_reason: "Intended Use Case",
        ph_name: "Anna Smith",
        ph_email: "anna@company.com",
        ph_company: "Acme Corp",
        ph_reason: "Briefly describe how you plan to use the MCP server...",
        legal_accept: "I accept the Terms of Use and acknowledge that I have read the Privacy Policy.",
        terms_link: "Terms of Use",
        privacy_link: "Privacy and Cookie Policy",
        contact_link: "Contact",
        btn_submit: "Submit Request",
        btn_submitting: "Submitting...",
        succ_title: "Thank you for your application!",
        succ_desc: "We have received your details and will contact you via email as soon as your dedicated key is approved.",
        footer_copy: "© 2026 MCP LAS — European labour law for AI Agents. Open source solution.",
        footer_disclaimer: "Built with Model Context Protocol (FastMCP) on Google Cloud Run & Firebase Firestore.",
        footer_report_bug: "Report a bug or feature request on GitHub"
      }
    };

    // ---------------------------------------------------------
    // Tools Database Definition (Bilingual)
    // ---------------------------------------------------------
    const TOOLS_DATA = [
      {
        id: "lookup_statute",
        icon: "fa-solid fa-magnifying-glass",
        categories: ["lag"],
        title: { sv: "Exakt Lagparagraf", en: "Exact Statute Section" },
        desc: {
          sv: "Hämtar ordagrann gällande lagtext och förarbetesnoter för specifik lag och paragraf (t.ex. LAS, MBL, Semesterlagen).",
          en: "Retrieves verbatim current statutory wording and legislative notes for any specific Swedish law and section (e.g. LAS, MBL, Annual Leave Act)."
        },
        prompt: {
          sv: "Vad säger LAS 7 § om sakliga skäl för uppsägning?",
          en: "What does LAS Section 7 say regarding objective grounds for dismissal?"
        }
      },
      {
        id: "search_labor_law",
        icon: "fa-solid fa-brain",
        categories: ["lag"],
        title: { sv: "Lagtextsökning", en: "Labor Law Search" },
        desc: {
          sv: "Semantisk AI-sökning och nyckelordssökning över hela den svenska arbetsrättsliga lagstiftningen.",
          en: "Semantic hybrid AI and keyword search across all Swedish employment and labor legislation."
        },
        prompt: {
          sv: "Vilka regler gäller för dygnsvila och raster enligt Arbetstidslagen?",
          en: "What are the rules for daily rest and breaks according to the Working Hours Act?"
        }
      },
      {
        id: "search_case_law",
        icon: "fa-solid fa-gavel",
        categories: ["lag"],
        title: { sv: "Domstolspraxis & Prejudikat", en: "Labour Court Case Law" },
        desc: {
          sv: "Söker bland 60 vägledande domar från Arbetsdomstolen (AD) vid tvister, sakliga skäl, personliga skäl, 29/29-principen eller arbetsbrist.",
          en: "Searches among 60 authoritative Labour Court (AD) precedents regarding objective grounds, personal misconduct, 29/29 principle, or redundancy."
        },
        prompt: {
          sv: "Finns det några AD-domar om uppsägning p.g.a. personliga skäl och samarbetssvårigheter?",
          en: "Are there any Labour Court rulings on dismissal due to personal reasons and workplace cooperation issues?"
        }
      },
      {
        id: "compare_statute_vs_cba",
        icon: "fa-solid fa-code-compare",
        categories: ["lag", "avtal"],
        title: { sv: "Jämför Lag vs Kollektivavtal", en: "Compare Statute vs CBA" },
        desc: {
          sv: "Ställer lagens minimiregler (t.ex. LAS) sida vid sida mot tillämpligt kollektivavtals förmånligare regler.",
          en: "Compares statutory baseline rules (e.g. LAS) side-by-side with more favorable collective agreement terms."
        },
        prompt: {
          sv: "Jämför uppsägningstiderna i LAS med Teknikavtalet för tjänstemän.",
          en: "Compare statutory notice periods in LAS with the Teknikföretagen collective agreement for white-collar staff."
        }
      },
      {
        id: "get_cba_exception",
        icon: "fa-solid fa-file-contract",
        categories: ["lag", "avtal"],
        title: { sv: "Avtalsundantag & Särregler", en: "CBA Deviations & Exceptions" },
        desc: {
          sv: "Kontrollerar specifika semidispositiva avtalsundantag för uppsägningstid, övertidskompensation och semester.",
          en: "Checks specific semi-dispositive CBA exceptions regarding notice periods, overtime pay, and vacation terms."
        },
        prompt: {
          sv: "Har Almega IT något undantag från LAS gällande uppsägningstid vid 5 års anställning?",
          en: "Does Almega IT have any deviation from statutory LAS notice periods after 5 years of employment?"
        }
      },
      {
        id: "calculate_vacation_pay",
        icon: "fa-solid fa-calculator",
        categories: ["semester"],
        title: { sv: "Semesterlön & Semestertillägg", en: "Vacation Pay & Supplement" },
        desc: {
          sv: "Beräknar semesterlön, semesterersättning och tillägg enligt Semesterlagen (sammalöneregeln 12 % / procentregeln) och Unionens avtalsregler (0,8 % fast lön, 0,5 % rörlig lön).",
          en: "Calculates vacation pay, compensation, and supplement under the Annual Leave Act (12% rule) and Unionen CBA rates (0.8% base salary, 0.5% variable salary)."
        },
        prompt: {
          sv: "Beräkna semesterlön för en anställd med 45 000 kr i månadslön, 25 semesterdagar och Unionens kollektivavtal.",
          en: "Calculate vacation pay for an employee earning 45,000 SEK/month with 25 vacation days under Unionen CBA."
        }
      },
      {
        id: "calculate_unpaid_vacation_deduction",
        icon: "fa-solid fa-money-bill-transfer",
        categories: ["semester"],
        title: { sv: "Semesterlöneavdrag (Obetald semester)", en: "Unpaid Vacation Salary Deduction" },
        desc: {
          sv: "Beräknar löneavdrag per obetald semesterdag (4,6 % enligt lag / kollektivavtal) vid nyanställning eller sparade dagar.",
          en: "Calculates monthly salary deductions per unpaid vacation day (4.6% standard) for new hires or unearned leave."
        },
        prompt: {
          sv: "Hur mycket dras från månadslönen om en anställd med 42 000 kr i månadslön tar 5 obetalda semesterdagar?",
          en: "How much salary is deducted if an employee earning 42,000 SEK/month takes 5 unpaid vacation days?"
        }
      },
      {
        id: "calculate_earned_vacation_days",
        icon: "fa-solid fa-calendar-day",
        categories: ["semester"],
        title: { sv: "Intjänade betalda semesterdagar", en: "Earned Paid Vacation Days" },
        desc: {
          sv: "Beräknar exakt antal intjänade betalda semesterdagar vid anställning under pågående intjänandeår (1 apr–31 mar el. kalenderår).",
          en: "Calculates exact earned paid vacation days when hired mid-year based on standard qualifying year (Apr 1–Mar 31 or calendar year)."
        },
        prompt: {
          sv: "Jag började min anställning 1 september och har 30 semesterdagar per år. Hur många betalda semesterdagar hinner jag tjäna in fram till 31 mars?",
          en: "I started employment on Sept 1st with 30 vacation days/year. How many paid vacation days will I earn by March 31st?"
        }
      },
      {
        id: "get_employer_certificate_info",
        icon: "fa-solid fa-file-invoice",
        categories: ["mallar", "lag"],
        title: { sv: "Arbetsgivarintyg & A-kassa", en: "Employer Certificate & Unemployment" },
        desc: {
          sv: "Visar lagkrav enligt 47 § lag om arbetslöshetsförsäkring (ALF) samt guidar till Sveriges a-kassors officiella digitala tjänst www.arbetsgivarintyg.nu.",
          en: "Details statutory requirements under Section 47 ALF and guides to the official Swedish portal www.arbetsgivarintyg.nu."
        },
        prompt: {
          sv: "Hur fungerar arbetsgivarintyg för a-kassa och är min arbetsgivare skyldig att ge mig det?",
          en: "How does the Swedish employer certificate for unemployment funds work and is the employer legally obliged to issue it?"
        }
      },
      {
        id: "get_rehabilitation_plan_info",
        icon: "fa-solid fa-heart-pulse",
        categories: ["mallar", "lag"],
        title: { sv: "Plan för återgång i arbete", en: "Return-to-Work Rehabilitation Plan" },
        desc: {
          sv: "Rehabiliteringsplan enligt 30 kap. 6 § SFB (senast dag 30 vid ≥ 60 dgr sjukdom) med direktlänk till Försäkringskassans blankett FK 7459 (PDF).",
          en: "Statutory rehabilitation plan under SFB Ch. 30 Sec. 6 (by day 30 for ≥ 60 days sick leave) with link to Social Insurance Agency form FK 7459."
        },
        prompt: {
          sv: "När måste en arbetsgivare upprätta en plan för återgång i arbete och var hittar jag blanketten (FK 7459)?",
          en: "When is an employer legally required to establish a return-to-work plan (FK 7459)?"
        }
      },
      {
        id: "get_discrimination_act_guide",
        icon: "fa-solid fa-shield-halved",
        categories: ["lag"],
        title: { sv: "Diskrimineringslagen & DO-Guide", en: "Discrimination Act & Equality Ombudsman" },
        desc: {
          sv: "Komplett guide till Diskrimineringslagens 7 diskrimineringsgrunder, 6 former av diskriminering samt aktiva åtgärder (3 kap.) och lönekartläggning.",
          en: "Comprehensive guide to the Discrimination Act's 7 protected grounds, 6 forms of discrimination, active measures, and mandatory pay equity audits."
        },
        prompt: {
          sv: "Vilka krav ställer Diskrimineringslagen på lönekartläggning och aktiva åtgärder för arbetsgivare med fler än 25 anställda?",
          en: "What requirements does the Discrimination Act place on pay equity audits and active measures for employers with 25+ staff?"
        }
      },
      {
        id: "check_bank_days_and_deadlines",
        icon: "fa-solid fa-calendar-check",
        categories: ["lag", "semester"],
        title: { sv: "Bankdagar & Helgdagar 2026", en: "Bank Days & Public Holidays 2026" },
        desc: {
          sv: "Kontrollerar bankdagar och helgdagar enligt Riksbankens officiella kalender 2026 för löneutbetalningar och lagstadgade tidsfrister.",
          en: "Checks official Swedish bank days and public holidays 2026 (Riksbank calendar) for pay day shifts and legal deadlines."
        },
        prompt: {
          sv: "Vilket datum ska lönen betalas ut i maj 2026 om den 25:e infaller på Pingstdagen?",
          en: "On which date should salary be paid in May 2026 if the 25th falls on a public holiday?"
        }
      },
      {
        id: "calculate_redundancy_turnorder_and_exceptions",
        icon: "fa-solid fa-users-gear",
        categories: ["turordning"],
        title: { sv: "Turordning & Undantagsberäkning", en: "Redundancy Turnorder & Exceptions" },
        desc: {
          sv: "Beräknar turordning vid arbetsbrist (LAS 22 § vs Unionens kollektivavtal), undantagsregler 1–4 inkl. procentregeln (15 % / 10 %), omplaceringsutredning (7 §) samt sorterar anställda i lagturlista.",
          en: "Calculates redundancy turnorder (LAS Sec. 22 vs Unionen CBA), exception rules 1–4 (15% / 10% rules), redeployment requirements (Sec. 7), and sorts seniority lists."
        },
        prompt: {
          sv: "Hur många personer får arbetsgivaren undanta från turordningslistan enligt Unionens kollektivavtal vid en arbetsbrist där 20 av 100 anställda berörs?",
          en: "How many employees may the employer exempt from the seniority list under Unionen CBA when 20 of 100 employees are affected by redundancy?"
        }
      },
      {
        id: "generate_turordningslista_excel",
        icon: "fa-solid fa-file-excel",
        categories: ["turordning"],
        title: { sv: "Skapa Turordningslista (Excel .xlsx)", en: "Generate Redundancy List (Excel .xlsx)" },
        desc: {
          sv: "Genererar och laddar ner en komplett formaterad Excel-arbetsbok (.xlsx) med ID-kolumner, beräkning av anställningsdagar via Excel-formler (=DATEDIF), sortering (sist in först ut, äldre före yngre) och automatisk färgkodning.",
          en: "Generates and downloads a fully formatted Excel workbook (.xlsx) with ID columns, automated tenure day formulas (=DATEDIF), sorting (LIFO, age tie-break), and status color-coding."
        },
        prompt: {
          sv: "Skapa en turordningslista i Excel för vårt företag med följande anställda och ladda ner den.",
          en: "Create a redundancy turnorder list in Excel for our company with the following employees and provide the download link."
        }
      },
      {
        id: "get_hr_document_template",
        icon: "fa-solid fa-file-lines",
        categories: ["mallar"],
        title: { sv: "HR-Dokumentmallar & Blanketter", en: "HR Document Templates & Forms" },
        desc: {
          sv: "Hämtar och fyller i officiella svenska arbetsrättsmallar enligt SKR / Arbetsgivarverket / LAS-standard: omplaceringsutredning (7 §), varsel om avskedande (30 §), besked om avskedande (18–19 §§), 69-årsregeln (32 a §), URA utlandsstationering, anställningsbevis (6 c §) och uppsägningsbesked.",
          en: "Generates official Swedish employment law forms under SKR / Arbetsgivarverket / LAS: redeployment audit (Sec. 7), dismissal notice (Sec. 30), summary dismissal (Sec. 18–19), age 69 termination (Sec. 32 a), employment contract (Sec. 6 c)."
        },
        prompt: {
          sv: "Ge mig en färdig mall för omplaceringsutredning enligt 7 § LAS som jag kan ladda ner och fylla i.",
          en: "Provide a complete official template for a redeployment investigation under Section 7 LAS that I can fill out."
        }
      },
      {
        id: "calculate_travel_deduction_and_mileage",
        icon: "fa-solid fa-car-side",
        categories: ["semester", "lag"],
        title: { sv: "Reseavdrag & Milersättning", en: "Travel Deduction & Mileage" },
        desc: {
          sv: "Beräknar Skatteverkets reseavdrag för resor till och från arbetet: egen bil (25 kr/mil), förmånsbil el (9,50 kr/mil) vs bensin/diesel (12 kr/mil), cykel (350 kr/år), självrisk (15 000 kr för 2026 / 11 000 kr för 2025) samt tidsvinstkrav (2 timmar/dag).",
          en: "Calculates Swedish Tax Agency (Skatteverket) commute deductions: private car (25 SEK/10 km), EV company car (9.50 SEK) vs fossil (12 SEK), bicycle, threshold (15,000 SEK 2026), and 2-hour daily time saving requirement."
        },
        prompt: {
          sv: "Hur mycket får jag göra i reseavdrag för deklarationen 2026 om jag pendlar 35 km enkel väg med egen bil 210 dagar och sparar 2,5 timmar per dag jämfört med bussen?",
          en: "How much travel deduction can I claim for the 2026 tax year if I commute 35 km one-way with my own car over 210 days and save 2.5 hours daily vs transit?"
        }
      },
      {
        id: "get_base_amounts_and_indices",
        icon: "fa-solid fa-chart-line",
        categories: ["semester", "lag"],
        title: { sv: "Prisbasbelopp & Inkomstbasbelopp", en: "Price Base Amount & Income Index" },
        desc: {
          sv: "Officiella basbelopp från SCB och Regeringen/Pensionsmyndigheten för 2026 (PBB 59 200 kr, IBB 83 400 kr, index 228,08, SGI-tak 592 000 kr, max PGI 56 050 kr/mån) med automatisk årlig synkronisering den 1 januari.",
          en: "Official Swedish statutory base amounts from Statistics Sweden (SCB) and Government for 2026 (PBB 59,200 SEK, IBB 83,400 SEK, index 228.08, sickness cap 592k, max pension salary 56,050/mo) with automated annual sync on Jan 1st."
        },
        prompt: {
          sv: "Vad är prisbasbeloppet och inkomstbasbeloppet för 2026 och hur påverkar det max SGI och pensionsgrundande inkomst?",
          en: "What are the price base amount and income base amount for 2026 and how do they determine the maximum SGI and pension qualifying income?"
        }
      },
      {
        id: "search_parliament_and_legislation",
        icon: "fa-solid fa-landmark-dome",
        categories: ["lag"],
        title: { sv: "Sök Riksdagsdokument & Förarbeten", en: "Search Parliament Docs & Legislative History" },
        desc: {
          sv: "Live-sökning i Riksdagens Öppna Data API (data.riksdagen.se) efter propositioner (prop), Statens offentliga utredningar (SOU), utskottsbetänkanden (bet), Departementsserien (Ds) och nya lagförslag.",
          en: "Live search in the Swedish Parliament Open Data API (data.riksdagen.se) for government bills (prop), SOU inquiries, parliamentary committee reports (bet), and legislative drafts."
        },
        prompt: {
          sv: "Sök efter regeringens propositioner och utredningar om anställningsskydd och turordningsregler.",
          en: "Search for government bills and official reports on employment protection and redundancy rules."
        }
      },
      {
        id: "get_parliament_document_details",
        icon: "fa-solid fa-file-shield",
        categories: ["lag"],
        title: { sv: "Riksdagsdokument Detaljer & Fulltext", en: "Parliament Document Details & Full Text" },
        desc: {
          sv: "Hämtar fullständig beslutsstatus, förslag, tidslinje/aktiviteter, relaterade bilagor (PDF) och textutdrag för ett specifikt riksdagsdokument (t.ex. Prop. 2021/22:176 eller HD03304).",
          en: "Retrieves complete legislative status, chamber proposals, timeline activities, PDF attachments, and full text for a specific parliamentary document (e.g. Prop. 2021/22:176 or HD03304)."
        },
        prompt: {
          sv: "Hämta detaljer och förslag för proposition Prop. 2021/22:176 (Flexibilitet, omställningsförmåga och trygghet på arbetsmarknaden).",
          en: "Fetch details and legislative proposals for bill Prop. 2021/22:176 regarding the new Employment Protection Act."
        }
      }
    ];

    // ---------------------------------------------------------
    // Language State & Switcher
    // ---------------------------------------------------------
    let currentLang = localStorage.getItem('mcp_lang') || 'sv';

    function setLanguage(lang) {
      if (lang !== 'sv' && lang !== 'en') lang = 'sv';
      currentLang = lang;
      localStorage.setItem('mcp_lang', lang);
      document.documentElement.lang = lang;

      // Update switcher buttons
      const btnSv = document.getElementById('langBtnSv');
      const btnEn = document.getElementById('langBtnEn');
      if (btnSv) btnSv.classList.toggle('active', lang === 'sv');
      if (btnEn) btnEn.classList.toggle('active', lang === 'en');

      // Update static text elements with data-i18n
      const dict = TRANSLATIONS[lang];
      document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (dict[key]) {
          el.innerHTML = dict[key];
        }
      });

      // Update placeholders
      document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (dict[key]) {
          el.placeholder = dict[key];
        }
      });

      const searchInput = document.getElementById('toolSearchInput');
      if (searchInput && dict.search_placeholder) {
        searchInput.placeholder = dict.search_placeholder;
      }

      // Re-render table in active language
      renderToolsTable();
      renderLiveCoverage();
    }

    // ---------------------------------------------------------
    // Mobile Hamburger Menu
    // ---------------------------------------------------------
    function toggleMobileMenu() {
      const menu = document.getElementById('navLinks');
      const btn = document.getElementById('mobileMenuBtn');
      const backdrop = document.getElementById('mobileMenuBackdrop');
      const icon = document.getElementById('mobileMenuIcon');
      const isOpen = menu.classList.toggle('open');
      backdrop.classList.toggle('open', isOpen);
      btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      icon.className = isOpen ? 'fa-solid fa-xmark' : 'fa-solid fa-bars';
      document.body.style.overflow = isOpen ? 'hidden' : '';
    }

    function closeMobileMenu() {
      const menu = document.getElementById('navLinks');
      if (!menu.classList.contains('open')) return;
      menu.classList.remove('open');
      document.getElementById('mobileMenuBackdrop').classList.remove('open');
      document.getElementById('mobileMenuBtn').setAttribute('aria-expanded', 'false');
      document.getElementById('mobileMenuIcon').className = 'fa-solid fa-bars';
      document.body.style.overflow = '';
    }

    window.addEventListener('resize', () => {
      if (window.innerWidth > 868) closeMobileMenu();
    });

    // ---------------------------------------------------------
    // Dark / Light Mode Theme Toggle
    // ---------------------------------------------------------
    const html = document.documentElement;
    const toggleBtn = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    const savedTheme = localStorage.getItem('mcp_theme') || 'light';

    function setTheme(theme) {
      if (theme === 'dark') {
        html.classList.add('dark');
        themeIcon.className = 'fa-solid fa-sun';
        localStorage.setItem('mcp_theme', 'dark');
      } else {
        html.classList.remove('dark');
        themeIcon.className = 'fa-solid fa-moon';
        localStorage.setItem('mcp_theme', 'light');
      }
    }
    setTheme(savedTheme);

    toggleBtn.addEventListener('click', () => {
      const isDark = html.classList.contains('dark');
      setTheme(isDark ? 'light' : 'dark');
    });

    // ---------------------------------------------------------
    // Tab Switcher for Connectors
    // ---------------------------------------------------------
    function switchTab(tabId) {
      document.querySelectorAll('.tab-pane').forEach(el => el.style.display = 'none');
      document.querySelectorAll('.tab-btn').forEach(el => {
        el.classList.remove('active');
        el.style.background = 'var(--card-bg)';
        el.style.color = 'var(--text-muted)';
      });
      const selectedPane = document.getElementById('tabContent-' + tabId);
      const selectedBtn = document.getElementById('tabBtn-' + tabId);
      if (selectedPane) selectedPane.style.display = 'block';
      if (selectedBtn) {
        selectedBtn.classList.add('active');
        selectedBtn.style.background = 'var(--brand-light)';
        selectedBtn.style.color = 'var(--brand-text)';
      }
    }

    // ---------------------------------------------------------
    // Copy Helpers
    // ---------------------------------------------------------
    function copyText(elementId, btn) {
      const el = document.getElementById(elementId);
      const text = el.innerText || el.textContent;
      navigator.clipboard.writeText(text.trim()).then(() => {
        const original = btn.innerHTML;
        const msg = currentLang === 'en' ? '<i class="fa-solid fa-check"></i> Copied!' : '<i class="fa-solid fa-check"></i> Kopierat!';
        btn.innerHTML = msg;
        setTimeout(() => { btn.innerHTML = original; }, 2000);
      }).catch(() => {
        alert(currentLang === 'en' ? 'Could not copy text.' : 'Kunde inte kopiera texten.');
      });
    }

    function copyPromptDirect(text, btn) {
      navigator.clipboard.writeText(text.trim()).then(() => {
        const original = btn.innerHTML;
        const msg = currentLang === 'en' ? '<i class="fa-solid fa-check" style="color: var(--brand);"></i> Copied!' : '<i class="fa-solid fa-check" style="color: var(--brand);"></i> Kopierat!';
        btn.innerHTML = msg;
        setTimeout(() => { btn.innerHTML = original; }, 2000);
      }).catch(() => {
        alert(currentLang === 'en' ? 'Could not copy prompt.' : 'Kunde inte kopiera prompten.');
      });
    }

    // ---------------------------------------------------------
    // Submit Application
    // ---------------------------------------------------------
    async function submitForm(e) {
      e.preventDefault();
      const btn = document.getElementById('submitBtn');
      btn.disabled = true;
      btn.innerText = currentLang === 'en' ? 'Submitting...' : 'Skickar...';

      const payload = {
        name: document.getElementById('name').value,
        email: document.getElementById('email').value,
        company: document.getElementById('company').value,
        reason: document.getElementById('reason').value,
        legal_accept: document.getElementById('legalAccept').checked
      };

      try {
        const res = await fetch('/api/request-key', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
          document.getElementById('keyForm').style.display = 'none';
          document.getElementById('formSuccess').style.display = 'block';
        } else {
          alert((currentLang === 'en' ? 'Error: ' : 'Fel: ') + data.message);
          btn.disabled = false;
          btn.innerText = currentLang === 'en' ? 'Submit Request' : 'Skicka ansökan';
        }
      } catch (err) {
        alert(currentLang === 'en' ? 'An error occurred during submission.' : 'Ett fel uppstod vid skickandet.');
        btn.disabled = false;
        btn.innerText = currentLang === 'en' ? 'Submit Request' : 'Skicka ansökan';
      }
    }

    // ---------------------------------------------------------
    // Tools Table Pagination, Search & Category Filter Logic
    // ---------------------------------------------------------
    let currentToolPage = 1;
    const toolsPerPage = 5;
    let currentCategory = 'all';
    let currentSearchTerm = '';

    function getMatchingTools() {
      return TOOLS_DATA.filter(tool => {
        const matchesCat = currentCategory === 'all' || tool.categories.includes(currentCategory);
        
        if (!currentSearchTerm) return matchesCat;
        
        const term = currentSearchTerm.toLowerCase();
        const titleText = (tool.title[currentLang] || tool.title.sv).toLowerCase();
        const descText = (tool.desc[currentLang] || tool.desc.sv).toLowerCase();
        const promptText = (tool.prompt[currentLang] || tool.prompt.sv).toLowerCase();
        const idText = tool.id.toLowerCase();
        
        const matchesSearch = titleText.includes(term) || descText.includes(term) || promptText.includes(term) || idText.includes(term);
        return matchesCat && matchesSearch;
      });
    }

    function renderToolsTable() {
      const tbody = document.getElementById('toolsTbody');
      if (!tbody) return;

      const matchingTools = getMatchingTools();
      const totalMatching = matchingTools.length;
      const totalPages = Math.ceil(totalMatching / toolsPerPage) || 1;

      if (currentToolPage > totalPages) currentToolPage = totalPages;
      if (currentToolPage < 1) currentToolPage = 1;

      const startIndex = (currentToolPage - 1) * toolsPerPage;
      const endIndex = startIndex + toolsPerPage;
      const pageTools = matchingTools.slice(startIndex, endIndex);

      const dict = TRANSLATIONS[currentLang];

      // Render table rows
      if (pageTools.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 2rem;">${dict.no_tools_found}</td></tr>`;
      } else {
        tbody.innerHTML = pageTools.map(tool => {
          const title = tool.title[currentLang] || tool.title.sv;
          const desc = tool.desc[currentLang] || tool.desc.sv;
          const prompt = tool.prompt[currentLang] || tool.prompt.sv;
          const safePrompt = prompt.replace(/'/g, "\\'").replace(/"/g, '&quot;');
          const copyLabel = dict.btn_copy;

          return `
            <tr class="tool-row">
              <td>
                <div class="tool-meta">
                  <div class="tool-icon-box"><i class="${tool.icon}"></i></div>
                  <div class="tool-title">
                    <span>${title}</span>
                    <span class="tool-badge">${tool.id}</span>
                  </div>
                </div>
              </td>
              <td>${desc}</td>
              <td>
                <div class="prompt-box">
                  <span class="prompt-text">"${prompt}"</span>
                  <button class="copy-prompt-btn" data-copy-prompt="${encodeURIComponent(prompt)}">
                    <i class="fa-regular fa-copy"></i> ${copyLabel}
                  </button>
                </div>
              </td>
            </tr>
          `;
        }).join('');
      }

      // Update info text
      const pageInfo = document.getElementById('pageInfoText');
      if (pageInfo) {
        if (totalMatching === 0) {
          pageInfo.innerText = dict.no_tools_found;
        } else {
          const startDisp = startIndex + 1;
          const endDisp = Math.min(endIndex, totalMatching);
          pageInfo.innerText = dict.showing_text(startDisp, endDisp, totalMatching);
        }
      }

      // Update pagination buttons
      const prevBtn = document.getElementById('prevPageBtn');
      const nextBtn = document.getElementById('nextPageBtn');
      if (prevBtn) prevBtn.disabled = currentToolPage <= 1;
      if (nextBtn) nextBtn.disabled = currentToolPage >= totalPages;

      // Render page numbers
      const numContainer = document.getElementById('paginationNumbers');
      if (numContainer) {
        numContainer.innerHTML = '';
        for (let i = 1; i <= totalPages; i++) {
          const numBtn = document.createElement('button');
          numBtn.className = 'btn btn-secondary';
          numBtn.innerText = i;
          numBtn.style.padding = '0.45rem 0.75rem';
          numBtn.style.fontSize = '0.85rem';
          numBtn.style.minWidth = '2.2rem';
          if (i === currentToolPage) {
            numBtn.style.background = 'var(--brand)';
            numBtn.style.color = '#ffffff';
            numBtn.style.borderColor = 'var(--brand)';
          }
          numBtn.onclick = () => {
            currentToolPage = i;
            renderToolsTable();
          };
          numContainer.appendChild(numBtn);
        }
      }

      // Update total badge
      const badge = document.getElementById('totalToolBadge');
      if (badge && currentCategory === 'all' && !currentSearchTerm) {
        badge.innerText = TOOLS_DATA.length;
      }
    }

    function handleToolSearch() {
      const input = document.getElementById('toolSearchInput');
      currentSearchTerm = input ? input.value.trim() : '';
      currentToolPage = 1;
      renderToolsTable();
    }

    function setCategoryFilter(category, btn) {
      currentCategory = category;
      currentToolPage = 1;
      document.querySelectorAll('.category-btn').forEach(b => {
        b.classList.remove('active');
        b.style.background = 'var(--card-bg)';
        b.style.color = 'var(--text)';
        b.style.borderColor = 'var(--card-border)';
      });
      if (btn) {
        btn.classList.add('active');
        btn.style.background = 'var(--brand-light)';
        btn.style.color = 'var(--brand-text)';
        btn.style.borderColor = 'rgba(34, 197, 94, 0.4)';
      }
      renderToolsTable();
    }

    function changePage(delta) {
      currentToolPage += delta;
      renderToolsTable();
    }

    let liveCoverage = null;

    function renderLiveCoverage() {
      if (!liveCoverage || !liveCoverage.jurisdictions) return;
      document.querySelectorAll('[data-coverage-desc]').forEach(node => {
        const country = liveCoverage.jurisdictions[node.dataset.coverageDesc];
        if (!country) return;
        const section_count = Number(country.section_count || 0);
        const synced = country.last_synced_at
          ? new Date(country.last_synced_at).toLocaleDateString(currentLang === 'en' ? 'en-GB' : 'sv-SE')
          : null;
        if (currentLang === 'en') {
          node.textContent = country.statutes
            ? `Live coverage: ${section_count.toLocaleString('en')} indexed sections${synced ? ` · synced ${synced}` : ''}.`
            : 'Source adapter available; no indexed sections yet.';
        } else {
          node.textContent = country.statutes
            ? `Aktuell täckning: ${section_count.toLocaleString('sv-SE')} indexerade paragrafer${synced ? ` · synkad ${synced}` : ''}.`
            : 'Källadapter finns; inga indexerade paragrafer ännu.';
        }
      });
    }

    async function loadLiveCoverage() {
      try {
        const response = await fetch('/api/coverage', { headers: { 'Accept': 'application/json' } });
        if (!response.ok) throw new Error('coverage unavailable');
        liveCoverage = await response.json();
        renderLiveCoverage();
      } catch (_) {
        document.querySelectorAll('[data-coverage-desc]').forEach(node => {
          node.textContent = currentLang === 'en'
            ? 'Live coverage is temporarily unavailable.'
            : 'Aktuell täckning är tillfälligt otillgänglig.';
        });
      }
    }

    // Initialize Language & Table
    document.addEventListener('DOMContentLoaded', () => {
      setLanguage(currentLang);
      loadLiveCoverage();
    });
    setLanguage(currentLang);
  
document.querySelector('[data-event-click="0"]').addEventListener('click', function(event) { toggleMobileMenu() });
document.querySelector('[data-event-click="1"]').addEventListener('click', function(event) { closeMobileMenu() });
document.querySelector('[data-event-click="2"]').addEventListener('click', function(event) { closeMobileMenu() });
document.querySelector('[data-event-click="3"]').addEventListener('click', function(event) { closeMobileMenu() });
document.querySelector('[data-event-click="4"]').addEventListener('click', function(event) { setLanguage('sv') });
document.querySelector('[data-event-click="5"]').addEventListener('click', function(event) { setLanguage('en') });
document.querySelector('[data-event-click="6"]').addEventListener('click', function(event) { closeMobileMenu() });
document.querySelector('[data-event-click="7"]').addEventListener('click', function(event) { closeMobileMenu() });
document.querySelector('[data-event-click="8"]').addEventListener('click', function(event) { switchTab('claude') });
document.querySelector('[data-event-click="9"]').addEventListener('click', function(event) { switchTab('chatgpt') });
document.querySelector('[data-event-click="10"]').addEventListener('click', function(event) { switchTab('gemini') });
document.querySelector('[data-event-click="11"]').addEventListener('click', function(event) { switchTab('cursor') });
document.querySelector('[data-event-click="12"]').addEventListener('click', function(event) { copyText('claudeUrl', this) });
document.querySelector('[data-event-click="13"]').addEventListener('click', function(event) { copyText('claudeConfig', this) });
document.querySelector('[data-event-click="14"]').addEventListener('click', function(event) { copyText('gptUrl', this) });
document.querySelector('[data-event-click="15"]').addEventListener('click', function(event) { copyText('gptPrompt', this) });
document.querySelector('[data-event-click="16"]').addEventListener('click', function(event) { copyText('geminiPrompt', this) });
document.querySelector('[data-event-click="17"]').addEventListener('click', function(event) { copyText('cursorConfig', this) });
document.querySelector('[data-event-input="18"]').addEventListener('input', function(event) { handleToolSearch() });
document.querySelector('[data-event-click="19"]').addEventListener('click', function(event) { setCategoryFilter('all', this) });
document.querySelector('[data-event-click="20"]').addEventListener('click', function(event) { setCategoryFilter('lag', this) });
document.querySelector('[data-event-click="21"]').addEventListener('click', function(event) { setCategoryFilter('semester', this) });
document.querySelector('[data-event-click="22"]').addEventListener('click', function(event) { setCategoryFilter('turordning', this) });
document.querySelector('[data-event-click="23"]').addEventListener('click', function(event) { setCategoryFilter('mallar', this) });
document.querySelector('[data-event-click="24"]').addEventListener('click', function(event) { changePage(-1) });
document.querySelector('[data-event-click="25"]').addEventListener('click', function(event) { changePage(1) });
document.querySelector('[data-event-submit="26"]').addEventListener('submit', function(event) { submitForm(event) });
document.addEventListener('click', function(event) {
  const button = event.target.closest('[data-copy-prompt]');
  if (button) copyPromptDirect(decodeURIComponent(button.dataset.copyPrompt), button);
});
