"""Hand-written display metadata for every Wayback Machine Collection Search collection.

The Wayback API (/__wb/search/collectioninfo) supplies counts, index dates and boilerplate
descriptions, but its titles are inconsistent ("geocities", ".gov web pages",
"hk.appledaily.com", 'Local Partisan News, AKA "Pink Slime"'). This table supplies a
consistent title + a one-line plain-English blurb + a category for each collection.

Keys are the collection ids used by /collection-search/<id>.
Fields:
  title    display title, title-case, no trailing "collection"/"web pages" noise
  blurb    one sentence: what this is and why it exists
  category one of CATEGORIES below
  kind     what a single search hit is (used for the unit label under the count)
"""

CATEGORIES = {
    "gov":      {"label": "U.S. Government",      "blurb": "Federal, state and local government material, including the End of Term transition crawls."},
    "press":    {"label": "Press Freedom",        "blurb": "Independent and exile newsrooms archived because they were shut down, blocked or seized."},
    "news":     {"label": "News & Journalism",    "blurb": "News corpora and the websites of outlets that have gone dark or shrunk."},
    "platform": {"label": "Platforms & Accounts", "blurb": "User-generated platforms and individual accounts captured as they closed or changed hands."},
    "format":   {"label": "Document Formats",     "blurb": "Web-wide indexes of a single file format, searchable by the text inside the documents."},
    "topic":    {"label": "Topics & Events",      "blurb": "Subject collections built around one event, organisation or country."},
}

CATEGORY_ORDER = ["gov", "press", "news", "platform", "format", "topic"]

CURATION = {
    # ---------------- U.S. Government ----------------
    "gov": dict(
        title=".gov Web Pages", category="gov", kind="web pages",
        blurb="Full-text index of pages captured from United States government domains — the "
              "broadest single view of the .gov web the Wayback Machine offers."),
    "gov-pdf": dict(
        title=".gov PDF Documents", category="gov", kind="PDF files",
        blurb="PDFs published on U.S. government domains, searchable by the text inside them "
              "rather than only by filename."),
    "congress.gov": dict(
        title="Congress.gov", category="gov", kind="web pages",
        blurb="The official site for U.S. federal legislation: bills, resolutions, roll-call "
              "votes and the Congressional Record."),
    "eric.ed.gov": dict(
        title="ERIC — Education Research", category="gov", kind="web pages",
        blurb="The U.S. Department of Education's Education Resources Information Center, the "
              "main bibliographic database for education research."),
    "files.eric.ed.gov": dict(
        title="ERIC Full-Text PDFs", category="gov", kind="PDF files",
        blurb="The research reports, papers and dissertations hosted on ERIC's document server, "
              "indexed by their full text."),
    "FOIAonline.gov": dict(
        title="FOIAonline Releases", category="gov", kind="PDF files",
        blurb="Records released through FOIAonline, the multi-agency U.S. FOIA request portal "
              "retired in 2023 — the released documents outlived the site."),
    "cia-world-factbook": dict(
        title="CIA World Factbook", category="gov", kind="web pages",
        blurb="Country profiles — geography, demographics, economy, military — published by the "
              "U.S. Central Intelligence Agency."),
    "us-state-department": dict(
        title="State Department on Twitter/X", category="gov", kind="posts",
        blurb="Archived Twitter/X posts from U.S. State Department accounts, including embassies "
              "and bureaus worldwide."),
    "EndOfTerm2008WebCrawls": dict(
        title="End of Term 2008", category="gov", kind="web pages",
        blurb="The first End of Term crawl: the U.S. federal web as it stood at the Bush-to-Obama "
              "transition, gathered with the California Digital Library."),
    "EndOfTerm2012WebCrawls": dict(
        title="End of Term 2012", category="gov", kind="web pages",
        blurb="The federal executive, legislative and judicial web captured at the close of "
              "President Obama's first term."),
    "EndOfTerm2016WebCrawls": dict(
        title="End of Term 2016", category="gov", kind="web pages",
        blurb="The federal web captured at the Obama-to-Trump transition, the crawl that drew "
              "wide attention to disappearing government data."),
    "EndOfTerm2020WebCrawls": dict(
        title="End of Term 2020", category="gov", kind="web pages",
        blurb="The federal web captured at the Trump-to-Biden transition — the largest End of "
              "Term crawl until 2024."),
    "EndOfTerm2024WebCrawls": dict(
        title="End of Term 2024", category="gov", kind="web pages",
        blurb="The federal web captured at the Biden-to-Trump transition, and the biggest End of "
              "Term crawl to date."),
    "EndOfTerm2024Videos": dict(
        title="End of Term 2024 Video", category="gov", kind="videos",
        blurb="Video files harvested from U.S. government sites during the 2024 transition crawl, "
              "searchable by surrounding page text."),

    # ---------------- Press Freedom ----------------
    "russian-independent-media": dict(
        title="Russian Independent Media", category="press", kind="articles",
        blurb="Reporting from Russian outlets blocked, branded \"undesirable\" or driven into "
              "exile, archived with PEN America's Russian Independent Media Archive."),
    "independent-media-belarus": dict(
        title="Independent Media Belarus", category="press", kind="articles",
        blurb="Belarusian outlets shut down, blocked or labelled extremist after the 2020 "
              "protests, crawled daily from a curated seed list."),
    "independent-media-afghanistan": dict(
        title="Independent Media Afghanistan", category="press", kind="articles",
        blurb="Afghan newsrooms archived daily since the Taliban's return to power, many of them "
              "now publishing from outside the country."),
    "independent-media-central-america": dict(
        title="Exile Media Central America", category="press", kind="articles",
        blurb="Central American newsrooms — notably Nicaraguan and Salvadoran — reporting from "
              "exile after raids, seizures and prosecutions."),
    "HongKong": dict(
        title="Hong Kong Shuttered Newsrooms", category="press", kind="web pages",
        blurb="A combined archive of Hong Kong news organisations that closed under the national "
              "security law: Apple Daily, Stand News, Citizen News and FactWire."),
    "hk.appledaily.com": dict(
        title="Apple Daily Hong Kong", category="press", kind="web pages",
        blurb="The pro-democracy tabloid forced to close in June 2021 after its assets were "
              "frozen and executives arrested."),
    "thestandnews.com": dict(
        title="Stand News", category="press", kind="web pages",
        blurb="The Hong Kong news site raided and closed in December 2021, whose editors were "
              "later convicted of sedition."),
    "hkcnews.com": dict(
        title="Citizen News Hong Kong", category="press", kind="web pages",
        blurb="Independent Hong Kong outlet founded by veteran journalists; it shut down in "
              "January 2022, citing the safety of its staff."),
    "zaman.com.tr": dict(
        title="Zaman (Turkey)", category="press", kind="articles",
        blurb="Turkey's largest-circulation daily until the state seized it in 2016 and closed it "
              "after that year's coup attempt."),
    "elperiodico.com.gt": dict(
        title="elPeriódico (Guatemala)", category="press", kind="web pages",
        blurb="The investigative Guatemalan daily that closed in 2023 after its publisher was "
              "jailed and its finances frozen."),
    "exiledonline.com": dict(
        title="The eXile", category="press", kind="web pages",
        blurb="The Moscow-based English-language paper shut down in 2008 after a government "
              "inspection — an early case of the pattern this shelf documents."),

    # ---------------- News & Journalism ----------------
    "mediacloud": dict(
        title="Media Cloud News Corpus", category="news", kind="articles",
        blurb="A continuously-crawled corpus of global online news, built with the Media Cloud "
              "research platform for studying how stories spread."),
    "local-news-us": dict(
        title="U.S. Local News", category="news", kind="web pages",
        blurb="Daily crawls of a seed list of local news outlets across the United States, "
              "capturing coverage in places losing their newspapers."),
    "towcenter-pink-slime-news-sites": dict(
        title="\"Pink Slime\" Local News", category="news", kind="web pages",
        blurb="Partisan, largely automated sites that present themselves as local newspapers, "
              "identified by Columbia's Tow Center for Digital Journalism."),
    "scmp.com": dict(
        title="South China Morning Post", category="news", kind="web pages",
        blurb="Hong Kong's English-language daily of record, archived across its shift from "
              "independent ownership to Alibaba."),
    "time.com": dict(
        title="TIME", category="news", kind="web pages",
        blurb="The American newsweekly's website, spanning several redesigns and changes of "
              "ownership."),
    "gawker.com": dict(
        title="Gawker", category="news", kind="web pages",
        blurb="The New York media-and-gossip site bankrupted by the Hulk Hogan verdict and shut "
              "down in 2016."),
    "vice.com": dict(
        title="VICE", category="news", kind="web pages",
        blurb="VICE's website as it stood before the 2023 bankruptcy and the retrenchment that "
              "followed it."),
    "mtv.com": dict(
        title="MTV News", category="news", kind="web pages",
        blurb="Two decades of MTV News reporting, deleted from the live web in 2024 when "
              "Paramount pulled the archive down."),
    "cmt.com": dict(
        title="CMT News", category="news", kind="web pages",
        blurb="Country Music Television's news site, taken offline in the same 2024 purge that "
              "removed MTV News."),
    "dcist.com": dict(
        title="DCist", category="news", kind="web pages",
        blurb="Washington, D.C. local news site — shut down once in 2017 and again in 2024, after "
              "WAMU closed it."),
    "themessenger.com": dict(
        title="The Messenger", category="news", kind="web pages",
        blurb="The heavily-funded U.S. news startup that launched in May 2023 and collapsed in "
              "January 2024, taking its site down with it."),

    # ---------------- Platforms & Accounts ----------------
    "geocities": dict(
        title="GeoCities", category="platform", kind="web pages",
        blurb="The 1990s personal-homepage community, crawled in a rush as Yahoo shut it down in "
              "2009 — the classic save-it-before-it-goes collection."),
    "telegram": dict(
        title="Telegram Public Channels", category="platform", kind="web pages",
        blurb="Archive Team's harvest of public Telegram channels and posts, by far the largest "
              "collection on this shelf."),
    "pastebin.com": dict(
        title="Pastebin", category="platform", kind="web pages",
        blurb="Public text pastes — snippets, configs, dumps and leaks — from the internet's "
              "default scratchpad."),
    "badoo.com": dict(
        title="Badoo Profiles", category="platform", kind="web pages",
        blurb="Public profile pages from the dating and social network, captured across more than "
              "a decade of the site."),
    "realdonaldtrump": dict(
        title="Donald Trump's Tweets", category="platform", kind="posts",
        blurb="Archived posts from @realDonaldTrump, including the years the account was "
              "suspended and its later reinstatement."),
    "poetry.com": dict(
        title="Poetry.com", category="platform", kind="web pages",
        blurb="The community poetry site's user-submitted archive, from the era when anyone could "
              "publish a poem and be told it had won something."),
    "tammybruce.com": dict(
        title="Tammy Bruce", category="platform", kind="web pages",
        blurb="The conservative commentator's personal site and blog, kept as a small, complete "
              "single-author archive."),

    # ---------------- Document Formats ----------------
    "pdf": dict(
        title="PDFs — Web-Wide", category="format", kind="PDF files",
        blurb="Every PDF the Wayback Machine has indexed, searchable by the document's own text "
              "as well as its URL and anchor text."),
    "presentations": dict(
        title="Presentation Decks", category="format", kind="files",
        blurb="PowerPoint, Keynote and OpenOffice Impress files captured from the web and indexed "
              "by their slide text."),

    # ---------------- Topics & Events ----------------
    "covid": dict(
        title="COVID-19 Research", category="topic", kind="web pages",
        blurb="Pandemic research repositories — NCBI, China's NGDC and NMDC — archived while the "
              "science was moving fastest."),
    "epstein-files": dict(
        title="The Epstein Files", category="topic", kind="PDF files",
        blurb="Government documents released in the Jeffrey Epstein matter, indexed page by page "
              "so the text is searchable, not just the filenames."),
    "northkorea": dict(
        title="North Korea", category="topic", kind="web pages",
        blurb="An Archive-It crawl of sites about and from the DPRK, including state media and "
              "outside monitoring projects."),
    "unicef": dict(
        title="UNICEF", category="topic", kind="web pages",
        blurb="The UN children's agency's global web presence, across country offices and "
              "reporting in many languages."),
}

# Collections that exist in the search index but are NOT offered in the
# web.archive.org drop-down. Found by diffing collectioninfo?collection=all.
UNLISTED_NOTE = {
    "nrc.gov": "U.S. Nuclear Regulatory Commission",
    "january6th.house.gov": "House Jan. 6 Select Committee",
}
