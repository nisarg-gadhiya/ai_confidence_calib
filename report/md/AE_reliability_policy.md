# Source-Reliability Policy

This appendix lists the complete source-reliability policy of the factual pipeline, generated from `factual/retrieval/source_reliability.py`. A host matches a listed domain if it equals the domain or ends with “.” followed by the domain; the longest matching domain wins. Hosts that match no listed domain are classified by the suffix rules in Chapter 8, then by the source type supplied upstream, and otherwise receive the *general* weight. @tab:policy-weights gives the weight, band and number of named domains of every tier, and @tab:policy-aliases the source-type labels accepted from other components.

Table: Tier weights and bands. {#tab:policy-weights}

| Tier | Weight | Band | Named domains |
|---|---|---|---|
| government | 0.97 | KEEP | 8 |
| intergovernmental | 0.95 | KEEP | 11 |
| academic | 0.93 | KEEP | 8 |
| scholarly publisher | 0.92 | KEEP | 39 |
| reference | 0.90 | KEEP | 16 |
| standards body | 0.88 | KEEP | 19 |
| preprint | 0.86 | KEEP | 6 |
| wire news | 0.84 | KEEP | 13 |
| reputable news | 0.82 | KEEP | 21 |
| encyclopedia wiki | 0.80 | KEEP | 3 |
| official docs | 0.78 | KEEP | 39 |
| institutional | 0.76 | KEEP | 18 |
| news | 0.70 | DOWN_WEIGHT | 29 |
| educational | 0.62 | DOWN_WEIGHT | 27 |
| technical qa | 0.58 | DOWN_WEIGHT | 8 |
| general org | 0.55 | DOWN_WEIGHT | 0 |
| general | 0.52 | DOWN_WEIGHT | 0 |
| blog | 0.48 | DOWN_WEIGHT | 12 |
| low trust tld | 0.40 | REJECT | 0 |
| forum | 0.38 | REJECT | 11 |
| social | 0.32 | REJECT | 12 |
| user wiki | 0.30 | REJECT | 4 |

Table: Source-type aliases accepted from upstream components. {#tab:policy-aliases}

| Alias | Tier |
|---|---|
| `gov` | government |
| `official` | government |
| `official_gov` | government |
| `intergov` | intergovernmental |
| `university` | academic |
| `edu` | academic |
| `journal` | scholarly publisher |
| `encyclopedia` | reference |
| `wire` | wire news |
| `documentation` | official docs |
| `docs` | official docs |
| `nonprofit` | institutional |
| `qa` | forum |
| `social_media` | social |

## Named Domains by Tier

**Government (0.97, KEEP).** `europa.eu`, `gc.ca`, `canada.ca`, `gouv.fr`, `bund.de`, `admin.ch`, `overheid.nl`, `regjeringen.no`.

**Intergovernmental (0.95, KEEP).** `un.org`, `unesco.org`, `unicef.org`, `worldbank.org`, `imf.org`, `oecd.org`, `wto.org`, `nato.int`, `icrc.org`, `iaea.org`, `ipcc.ch`.

**Academic (0.93, KEEP).** `ox.ac.uk`, `cam.ac.uk`, `ethz.ch`, `epfl.ch`, `mpg.de`, `cnrs.fr`, `csiro.au`, `riken.jp`.

**Scholarly publisher (0.92, KEEP).** `nature.com`, `science.org`, `sciencedirect.com`, `springer.com`, `link.springer.com`, `wiley.com`, `onlinelibrary.wiley.com`, `tandfonline.com`, `sagepub.com`, `jstor.org`, `ieee.org`, `ieeexplore.ieee.org`, `acm.org`, `dl.acm.org`, `plos.org`, `cell.com`, `thelancet.com`, `nejm.org`, `bmj.com`, `jamanetwork.com`, `pnas.org`, `oup.com`, `academic.oup.com`, `cambridge.org`, `frontiersin.org`, `mdpi.com`, `aps.org`, `acs.org`, `rsc.org`, `iop.org`, `semanticscholar.org`, `doi.org`, `europepmc.org`, `cochranelibrary.com`, `aclanthology.org`, `openreview.net`, `proceedings.mlr.press`, `neurips.cc`, `jmlr.org`.

**Reference (0.90, KEEP).** `britannica.com`, `oxfordreference.com`, `merriam-webster.com`, `dictionary.cambridge.org`, `oed.com`, `worldbook.com`, `encyclopedia.com`, `ebsco.com`, `mathworld.wolfram.com`, `wolframalpha.com`, `ourworldindata.org`, `statista.com`, `history.com`, `guinnessworldrecords.com`, `nobelprize.org`, `imdb.com`.

**Standards body (0.88, KEEP).** `iso.org`, `w3.org`, `ietf.org`, `rfc-editor.org`, `unicode.org`, `ecma-international.org`, `asme.org`, `ashrae.org`, `iec.ch`, `itu.int`, `ansi.org`, `ama-assn.org`, `acponline.org`, `heart.org`, `cancer.org`, `mayoclinic.org`, `clevelandclinic.org`, `hopkinsmedicine.org`, `nhs.uk`.

**Preprint (0.86, KEEP).** `arxiv.org`, `biorxiv.org`, `medrxiv.org`, `ssrn.com`, `researchgate.net`, `papers.nips.cc`.

**Wire news (0.84, KEEP).** `reuters.com`, `apnews.com`, `afp.com`, `bbc.co.uk`, `bbc.com`, `npr.org`, `pbs.org`, `abc.net.au`, `cbc.ca`, `dw.com`, `france24.com`, `nhk.or.jp`, `rnz.co.nz`.

**Reputable news (0.82, KEEP).** `nytimes.com`, `washingtonpost.com`, `theguardian.com`, `wsj.com`, `ft.com`, `economist.com`, `bloomberg.com`, `theatlantic.com`, `newyorker.com`, `latimes.com`, `theglobeandmail.com`, `thehindu.com`, `indianexpress.com`, `scmp.com`, `aljazeera.com`, `lemonde.fr`, `spiegel.de`, `smh.com.au`, `scientificamerican.com`, `newscientist.com`, `technologyreview.com`.

**Encyclopedia wiki (0.80, KEEP).** `wikipedia.org`, `wikimedia.org`, `wikidata.org`.

**Official docs (0.78, KEEP).** `docs.python.org`, `python.org`, `developer.mozilla.org`, `learn.microsoft.com`, `docs.microsoft.com`, `developer.apple.com`, `developer.android.com`, `cloud.google.com`, `developers.google.com`, `ai.google.dev`, `docs.aws.amazon.com`, `aws.amazon.com`, `developer.nvidia.com`, `docs.nvidia.com`, `ibm.com`, `oracle.com`, `docs.oracle.com`, `pytorch.org`, `tensorflow.org`, `keras.io`, `scikit-learn.org`, `numpy.org`, `pandas.pydata.org`, `react.dev`, `nodejs.org`, `rust-lang.org`, `go.dev`, `kubernetes.io`, `docker.com`, `postgresql.org`, `mysql.com`, `linux.org`, `kernel.org`, `gnu.org`, `huggingface.co`, `openai.com`, `anthropic.com`, `deepmind.google`, `research.google`.

**Institutional (0.76, KEEP).** `smithsonianmag.com`, `si.edu`, `nationalgeographic.com`, `metmuseum.org`, `britishmuseum.org`, `amnh.org`, `khanacademy.org`, `pewresearch.org`, `brookings.edu`, `rand.org`, `carnegieendowment.org`, `amnesty.org`, `hrw.org`, `redcross.org`, `wwf.org`, `iucn.org`, `audubon.org`, `exploratorium.edu`.

**News (0.70, DOWN_WEIGHT).** `cnn.com`, `nbcnews.com`, `cbsnews.com`, `abcnews.go.com`, `usatoday.com`, `time.com`, `newsweek.com`, `forbes.com`, `businessinsider.com`, `cnbc.com`, `vox.com`, `axios.com`, `politico.com`, `thehill.com`, `independent.co.uk`, `telegraph.co.uk`, `skynews.com`, `ndtv.com`, `hindustantimes.com`, `timesofindia.indiatimes.com`, `wired.com`, `arstechnica.com`, `theverge.com`, `techcrunch.com`, `zdnet.com`, `livescience.com`, `space.com`, `sciencedaily.com`, `phys.org`.

**Educational (0.62, DOWN_WEIGHT).** `investopedia.com`, `howstuffworks.com`, `worldatlas.com`, `geeksforgeeks.org`, `w3schools.com`, `tutorialspoint.com`, `towardsdatascience.com`, `machinelearningmastery.com`, `simplilearn.com`, `datacamp.com`, `coursera.org`, `edx.org`, `byjus.com`, `chem.libretexts.org`, `libretexts.org`, `sparknotes.com`, `cliffsnotes.com`, `study.com`, `thoughtco.com`, `verywellhealth.com`, `healthline.com`, `webmd.com`, `medicalnewstoday.com`, `infoplease.com`, `factmonster.com`, `countryreports.org`, `nationsonline.org`.

**Technical qa (0.58, DOWN_WEIGHT).** `stackoverflow.com`, `stackexchange.com`, `superuser.com`, `serverfault.com`, `askubuntu.com`, `mathoverflow.net`, `github.com`, `gitlab.com`.

**Blog (0.48, DOWN_WEIGHT).** `medium.com`, `substack.com`, `blogspot.com`, `wordpress.com`, `tumblr.com`, `wixsite.com`, `weebly.com`, `hashnode.dev`, `dev.to`, `ghost.io`, `squarespace.com`, `linkedin.com`.

**Forum (0.38, REJECT).** `reddit.com`, `quora.com`, `answers.com`, `answers.yahoo.com`, `ask.com`, `chegg.com`, `brainly.com`, `brainly.in`, `coursehero.com`, `4chan.org`, `boards.ie`.

**Social (0.32, REJECT).** `twitter.com`, `x.com`, `facebook.com`, `instagram.com`, `tiktok.com`, `youtube.com`, `youtu.be`, `pinterest.com`, `threads.net`, `snapchat.com`, `telegram.org`, `t.me`.

**User wiki (0.30, REJECT).** `fandom.com`, `wikia.com`, `wikihow.com`, `everybodywiki.com`.

## Suffix Rules

- Government top-level domains: `.gov`, `.mil`; government second-level labels under a two-letter country code: `go`, `gob`, `gouv`, `gov`, `govt`, `gv`, `mil`, `nic`.
- Intergovernmental top-level domain: `.int`.
- Academic top-level domain: `.edu`; academic second-level labels under a country code: `ac`, `edu`, `uni`.
- Blog: host beginning with `blog.` or `blog-`.
- Low-trust top-level domains: `.biz`, `.buzz`, `.cf`, `.click`, `.cyou`, `.fit`, `.ga`, `.gq`, `.icu`, `.info`, `.loan`, `.ml`, `.monster`, `.rest`, `.tk`, `.top`, `.work`, `.xyz`.
- General organisation: other `.net`, `.org` hosts.
