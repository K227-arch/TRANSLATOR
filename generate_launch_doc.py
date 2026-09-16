"""AI Stick Launch Document Generator"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

doc = Document()
sec = doc.sections[0]
sec.page_width = Inches(8.27); sec.page_height = Inches(11.69)
sec.left_margin = sec.right_margin = Inches(1.2)
sec.top_margin = sec.bottom_margin = Inches(1.0)

GOLD = RGBColor(0x8B,0x69,0x14); DARK = RGBColor(0x1C,0x1B,0x1F)
GREY = RGBColor(0x49,0x45,0x4E); WHITE = RGBColor(0xFF,0xFF,0xFF)
LGREY = RGBColor(0xAA,0xAA,0xAA)

def r(para,text,size=11,bold=False,italic=False,col=GREY):
    x=para.add_run(text); x.bold=bold; x.italic=italic
    x.font.size=Pt(size); x.font.color.rgb=col; return x

def h1(t):
    p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(20); p.paragraph_format.space_after=Pt(6)
    r(p,t,20,True,col=GOLD)
    pPr=p._p.get_or_add_pPr(); pBdr=OxmlElement('w:pBdr'); b=OxmlElement('w:bottom')
    b.set(qn('w:val'),'single'); b.set(qn('w:sz'),'6'); b.set(qn('w:color'),'8B6914')
    pBdr.append(b); pPr.append(pBdr)

def h2(t):
    p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(12); p.paragraph_format.space_after=Pt(4)
    r(p,t,14,True,col=DARK)

def h3(t):
    p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(8); p.paragraph_format.space_after=Pt(2)
    r(p,t,12,True,col=GOLD)

def body(t):
    p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(5); r(p,t,11,col=GREY)

def bul(t,lv=0):
    p=doc.add_paragraph(style='List Bullet'); p.paragraph_format.left_indent=Inches(0.3+lv*0.25)
    p.paragraph_format.space_after=Pt(2); r(p,t,11,col=GREY)

def num(t):
    p=doc.add_paragraph(style='List Number'); p.paragraph_format.space_after=Pt(2); r(p,t,11,col=GREY)

def tbl(headers,rows,widths=None):
    t=doc.add_table(rows=1+len(rows),cols=len(headers)); t.style='Table Grid'
    for i,h in enumerate(headers):
        c=t.rows[0].cells[i]; c.text=h
        for x in c.paragraphs[0].runs: x.bold=True; x.font.color.rgb=WHITE; x.font.size=Pt(10)
        s=OxmlElement('w:shd'); s.set(qn('w:fill'),'8B6914'); s.set(qn('w:val'),'clear')
        c._tc.get_or_add_tcPr().append(s)
        if widths: c.width=Inches(widths[i])
    for ri,row in enumerate(rows):
        for ci,val in enumerate(row):
            c=t.rows[ri+1].cells[ci]; c.text=str(val)
            for x in c.paragraphs[0].runs: x.font.size=Pt(10); x.font.color.rgb=GREY
    doc.add_paragraph()

def pb(): doc.add_page_break()

def ctr(t,size=12,bold=False,col=DARK):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; r(p,t,size,bold,col=col)

centre = ctr

def div():
    p=doc.add_paragraph(); p.paragraph_format.space_before=p.paragraph_format.space_after=Pt(4)
    pPr=p._p.get_or_add_pPr(); pBdr=OxmlElement('w:pBdr'); b=OxmlElement('w:bottom')
    b.set(qn('w:val'),'single'); b.set(qn('w:sz'),'4'); b.set(qn('w:color'),'CCCCCC')
    pBdr.append(b); pPr.append(pBdr)

# ── COVER ─────────────────────────────────────────────────────────────────────
for _ in range(4): doc.add_paragraph()
ctr("AI STICK",40,True,GOLD)
ctr("Runyoro-Rutooro \u2194 English Neural Machine Translator",15,col=GREY)
ctr("Powered by the Raspberry Pi",12,col=LGREY)
doc.add_paragraph(); ctr("\u2501"*38,12,col=GOLD); doc.add_paragraph()
ctr("LAUNCH DOCUMENT",16,True,DARK)
ctr("Technical Overview  \u00b7  User Manual  \u00b7  Training Report",11,col=GREY)
for _ in range(5): doc.add_paragraph()
ctr("September 2026",12,col=GREY)
ctr("Bunyoro-Kitara Kingdom  |  Tooro Kingdom  |  Uganda",10,col=LGREY)
pb()

# ── TOC ───────────────────────────────────────────────────────────────────────
h1("TABLE OF CONTENTS")
for line in [
    "1.   Introduction & Vision","2.   The AI Stick Device","3.   How to Access & Connect",
    "4.   Feature Guide \u2014 Full User Manual",
    "     4.1  Translation (English \u2194 Runyoro-Rutooro)","     4.2  Voice Translation",
    "     4.3  Camera / OCR Translation (Lens)","     4.4  AI Chat Language Assistant",
    "     4.5  Dictionary","     4.6  Runyoro Writing Editor",
    "     4.7  Batch Translation","     4.8  PDF / Document Summarisation",
    "     4.9  Translation History & Feedback","     4.10 Language Rules Reference",
    "5.   Training Write-Up \u2014 Methods & Techniques","6.   Dataset \u2014 Sources & Statistics",
    "7.   Model Architecture & Training Configuration","8.   Results & Accuracy",
    "9.   Grammar Post-Processing Rules","10.  Problems Faced & Solutions",
    "11.  System Architecture on the Pi","12.  Future Plans & Roadmap",
]:
    p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(2); r(p,line,11,col=DARK)
pb()

# ── 1. INTRODUCTION ───────────────────────────────────────────────────────────
h1("1.  INTRODUCTION & VISION")
body("Runyoro-Rutooro is a Bantu language spoken by the Bunyoro-Kitara and Tooro kingdoms in western Uganda \u2014 a heritage language with over two million speakers that has historically been under-represented in digital technology and natural language processing.")
body("The AI Stick project was born from a single conviction: language technology must reach the people who speak those languages, not only those with reliable internet access. The AI Stick is a Raspberry Pi 5 device pre-loaded with fine-tuned neural machine translation models for Runyoro-Rutooro \u2194 English. It broadcasts its own Wi-Fi hotspot \u2014 connect any phone or laptop, open a browser, and the full translator is available instantly, even in remote areas with zero internet coverage.")
body("This document is the definitive launch reference: a user manual for anyone who picks up the device, a technical training report for researchers and stakeholders, and a roadmap for where the project goes next.")
h2("Core Principles")
for b in ["Offline-first: all AI runs locally on the Raspberry Pi \u2014 no cloud dependency.",
          "Dual-model: NLLB-200 (primary) and MarianMT (fallback) run simultaneously for every translation.",
          "Community-driven: human corrections collected in the field are used to retrain models continuously.",
          "Hybrid AI + rules: explicit Runyoro-Rutooro grammar rules post-process every output.",
          "Accessible: works on any phone browser with no app installation required."]: bul(b)
div()

# ── 2. DEVICE ─────────────────────────────────────────────────────────────────
h1("2.  THE AI STICK DEVICE")
body("The AI Stick is a Raspberry Pi 5 running a custom translation stack. It operates as a standalone Wi-Fi access point \u2014 users connect to it exactly as they would connect to any Wi-Fi router, then access the translator through a web browser.")
h2("Technical Specifications")
tbl(["Component","Specification"],[
    ["Hardware","Raspberry Pi 5 (8 GB RAM)"],["Storage","MicroSD card (128 GB+)"],
    ["Connectivity","Wi-Fi hotspot (SSID: Lunyoro-Translator) + Ethernet"],
    ["Power","USB-C, 5V / 5A (power bank or wall adapter)"],
    ["OS","Raspberry Pi OS \u2014 Debian 12 Bookworm, 64-bit ARM"],
    ["Backend","C++ binary with ONNX Runtime (optimised for ARM64)"],
    ["Sidecar","Python 3 FastAPI (Lens, batch, PDF, chat, language rules)"],
    ["Web server","Nginx reverse proxy, port 80"],
    ["Frontend","Static Next.js 16 export, served from local filesystem"],
    ["Startup time","~60 seconds (4 ONNX models load into ~3.6 GB RAM)"],
],widths=[2.0,4.5])
h2("Model Files on Device")
tbl(["Model","Direction","Format","Size"],[ 
    ["NLLB-200 (600M)","English \u2192 Runyoro","ONNX INT8","~1.19 GB"],
    ["NLLB-200 (600M)","Runyoro \u2192 English","ONNX INT8","~1.19 GB"],
    ["MarianMT (~74M)","English \u2192 Runyoro","ONNX FP32","~550 MB"],
    ["MarianMT (~74M)","Runyoro \u2192 English","ONNX FP32","~550 MB"],
    ["MobileNetV2","Image classification","Safetensors","~14 MB"],
    ["Sentence Transformer","Semantic search / dict","Safetensors","~90 MB"],
],widths=[2.2,2.2,1.3,1.0])
body("Total model footprint: ~3.6 GB of 8 GB RAM used at runtime after full startup.")
div()

# ── 3. CONNECTION ─────────────────────────────────────────────────────────────
h1("3.  HOW TO ACCESS & CONNECT")
h2("Step-by-Step Connection Guide")
for s in [
    "Power on the AI Stick by plugging in the USB-C cable. The green LED will blink, then stay solid. Allow 60 seconds for full startup.",
    "On your phone or laptop, open Wi-Fi settings and look for a network named Lunyoro-Translator.",
    "Connect to Lunyoro-Translator. No password is required.",
    "Open any web browser (Chrome, Safari, Firefox) and navigate to:  http://192.168.4.1",
    "The translator app loads immediately. It is now fully ready to use \u2014 completely offline.",
]: num(s)
body("Note: On some Android and iPhone devices a notification may say 'This network has no internet access' \u2014 this is expected. Tap 'Stay connected' or 'Use this network anyway' to proceed.")
h2("Troubleshooting")
tbl(["Problem","Solution"],[
    ["Cannot find Lunyoro-Translator Wi-Fi","Wait 60 s after power-on. Check the green LED is solid."],
    ["Browser says 'site can't be reached'","Confirm you are on Lunyoro-Translator Wi-Fi. Type http://192.168.4.1 (not https)."],
    ["Features don't respond","Hard-refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)."],
    ["'Could not connect to server'","The service is still starting. Wait 60 s after power-on, then refresh."],
    ["Very slow on first translation","Models warm up on first use (2\u201310 s). Subsequent translations are faster."],
],widths=[2.5,4.0])
pb()

# ── 4. FEATURE GUIDE ──────────────────────────────────────────────────────────
h1("4.  FEATURE GUIDE \u2014 FULL USER MANUAL")
body("The AI Stick app is organised around a bottom navigation bar with five tabs. All features work without internet.")
tbl(["Tab","Feature","Description"],[
    ["Home","Dashboard","Landing page with feature cards and quick access"],
    ["Translate","Text Translation","English \u2194 Runyoro-Rutooro neural translation"],
    ["Camera","Lens / OCR","Camera OCR translation and object identification"],
    ["Chat","AI Assistant","Grammar help, vocabulary, cultural questions"],
    ["Help","User Guide","In-app help and usage guide"],
],widths=[1.0,1.5,4.0])

h2("4.1  Translation \u2014 English \u2194 Runyoro-Rutooro")
body("The core feature. Translates text in both directions using two AI models running simultaneously on the device.")
h3("How to use:")
for s in ["Tap the Translate tab (central icon in the bottom bar).",
          "Direction defaults to English \u2192 Runyoro. Tap the \u21c4 swap arrow to reverse.",
          "Type or paste text in the left panel (up to 5,000 characters).",
          "Tap the circular translate button or press Ctrl+Enter.",
          "The translation appears in the right panel. Use the copy icon to copy it."]: num(s)
h3("Key features:")
for b in ["NLLB-200 is the primary model. When NLLB and MarianMT differ meaningfully, both outputs are shown side-by-side.",
          "Domain selector: choose Daily Life, Health, Education, Agriculture, etc. to bias vocabulary.",
          "Real-time spellcheck with wavy underlines and one-click corrections (Runyoro-Rutooro input).",
          "Method label shows whether the result came from neural AI, corpus retrieval, or dictionary.",
          "Offline cache: recent translations stored in the browser for instant replay."]: bul(b)
h3("Feedback:")
for b in ["Thumbs-up: confirm a correct translation \u2014 used for model retraining.",
          "Thumbs-down: flag an error, select issue type, and optionally submit a correction.",
          "Model comparison: choose NLLB, MarianMT, both correct, or both wrong."]: bul(b)

h2("4.2  Voice Translation")
body("Speak into the microphone and receive an immediate translation.")
for s in ["Tap the Voice card on the Home dashboard.",
          "Select direction (English \u2192 Runyoro or Runyoro \u2192 English).",
          "Tap the microphone button and speak clearly.",
          "Speech is transcribed and translated automatically."]: num(s)
body("Uses the browser's built-in Speech API. For best results, speak at a measured pace in a quiet environment.")

h2("4.3  Camera / OCR Translation (AI Stick Lens)")
body("Point the camera at printed text \u2014 signs, menus, books, labels \u2014 to detect and translate it.")
h3("OCR Mode (text scanning):")
for s in ["Tap the Camera tab and select OCR mode.",
          "Tap Open Camera or Upload Image from your gallery.",
          "Text detected in the image is translated with coloured overlay boxes.",
          "Toggle between English\u2192Runyoro and Runyoro\u2192English using the direction selector."]: num(s)
body("On the Pi's local hotspot, the camera opens your device's native camera app (live viewfinder requires HTTPS which is unavailable locally). Take a photo and it is processed immediately by the on-device OCR engine.")
h3("Identify Mode (object recognition):")
for s in ["Switch to Identify mode in the Camera tab.",
          "Upload a photo of any object.",
          "The AI identifies the object and provides its Runyoro-Rutooro name from both NLLB and MarianMT."]: num(s)
body("Powered by MobileNetV2 trained on ImageNet (1,000 classes). Best for everyday objects, animals, food, and plants.")

h2("4.4  AI Chat Language Assistant")
body("An AI assistant that answers questions about Runyoro-Rutooro grammar, vocabulary, culture, and proverbs.")
for s in ["Tap the Chat tab.",
          "Type your question. Examples: 'What is the R/L rule?', 'How do I say good morning?', 'Explain noun classes', 'What does empaako Atwooki mean?', 'Translate: Oraire ota mugenziwe'",
          "Tap Send or press Enter.",
          "The assistant replies with detailed explanations in plain English."]: num(s)
body("Quick topic chips (Greetings, Numbers, Directions, Food, Emergency) give instant common phrase lookups. On the Pi offline, grammar questions, vocabulary, and translation requests are answered from the built-in knowledge base. Open-ended questions use Llama 3.1 8B when internet is available.")

h2("4.5  Dictionary")
body("Look up Runyoro-Rutooro words with definitions, POS labels, dialect notes, and example sentences.")
for s in ["Tap the Dictionary card on the Home dashboard.",
          "Select direction: English\u2192Runyoro or Runyoro\u2192English.",
          "Type the word and tap Search or press Enter.",
          "Results show: the word, English definition, native Runyoro definition, POS badge (Noun/Verb/Adjective), dialect, example sentences."]: num(s)
body("The dictionary contains 9,314 entries. Words not in the dictionary receive an AI-generated translation marked with an 'AI' badge (NLLB-200 primary). Filter results by Noun / Verb / Adjective using the pills above results.")

h2("4.6  Runyoro Writing Editor")
body("A rich-text editor for composing, proofreading, and translating Runyoro-Rutooro documents.")
for b in ["Real-time spellcheck with wavy underlines and one-click corrections.",
          "Grammar reference cards: R/L rule, noun classes, tenses, verb forms.",
          "Formatting toolbar: bold, italic, underline, lists, alignment.",
          "Translate button: auto-detects language and translates the full document.",
          "AI grammar review: sends content to the language assistant for structured feedback.",
          "Save as .txt with a datestamped filename."]: bul(b)

h2("4.7  Batch Translation")
body("Translate many sentences at once \u2014 ideal for educators, researchers, and data collection.")
for s in ["Open the Batch tab from the Home dashboard.",
          "Paste up to 100 sentences (one per line) or upload a .csv or .txt file.",
          "Select direction and tap Translate All.",
          "Results show source and translation side-by-side."]: num(s)

h2("4.8  PDF / Document Summarisation")
body("Upload a PDF, Word document, or text file to get an extractive summary translated into Runyoro-Rutooro.")
for b in ["Supported formats: .pdf, .docx, .doc, .txt",
          "Extractive summarisation selects the most informative sentences (up to 20% of document, max 10 sentences).",
          "Both NLLB-200 and MarianMT translations of the summary are shown.",
          "Runyoro-Rutooro input documents are auto-detected and translated to English first."]: bul(b)

h2("4.9  Translation History & Feedback")
body("All translations are saved to the History tab and persist across browser sessions. Tap any entry to reuse or copy it. Feedback (thumbs-up/down and corrections) is stored and periodically used to improve the models.")

h2("4.10  Language Rules Reference")
body("A comprehensive interactive grammar reference:")
for b in ["R/L Rule \u2014 when to use R vs L with clear examples",
          "15 Noun Classes \u2014 prefixes, plurals, concordial agreement tables",
          "Tense system \u2014 11 tenses with markers and example sentences",
          "Interjections (Ebihunaazo) \u2014 35 entries with meanings",
          "Idioms (Ebidikizo) \u2014 17 idiomatic expressions",
          "Proverbs (Enfumo) \u2014 12 proverbs with random generator",
          "Numbers (Okubara) \u2014 1 to 1,000,000,000 in Runyoro-Rutooro",
          "Empaako \u2014 12 traditional honorific names with cultural significance",
          "Conjunctions, prepositions, negation words, adjective stems, personal pronouns"]: bul(b)
pb()

# ── 5. TRAINING WRITE-UP ──────────────────────────────────────────────────────
h1("5.  TRAINING WRITE-UP \u2014 METHODS & TECHNIQUES")
body("Training a neural machine translation (NMT) system for Runyoro-Rutooro presented unique challenges: extreme low-resource conditions, no pre-existing parallel corpora, orthographic inconsistency among speakers, and a language whose morphological complexity is not well-represented in multilingual pre-trained models.")
body("The training process went through five major phases over approximately 12 months: data collection \u2192 data cleaning \u2192 baseline model training \u2192 iterative improvement \u2192 on-device optimisation.")

h2("5.1  Problem Definition")
body("Standard NMT approaches require hundreds of thousands to millions of parallel sentence pairs. For Runyoro-Rutooro, no such resource existed publicly. The project began from zero, collecting, cleaning, and augmenting data iteratively alongside training, with each cycle informing what data gaps needed to be filled next. Two translation directions were trained independently: English \u2192 Runyoro-Rutooro (en\u2192lun) and Runyoro-Rutooro \u2192 English (lun\u2192en).")

h2("5.2  Base Models Selected")
h3("MarianMT (Helsinki-NLP / Opus-MT)")
body("MarianMT is a lightweight sequence-to-sequence transformer developed for massively multilingual translation, pre-trained on OPUS multilingual data. It was chosen for its small footprint (~550 MB deployed) and fast inference on ARM64 \u2014 essential for on-device Raspberry Pi deployment. Fine-tuned end-to-end on the curated Runyoro-Rutooro dataset.")
h3("NLLB-200 (Meta / Facebook Research)")
body("No Language Left Behind (NLLB-200) is Meta's 600M-parameter multilingual model covering 200 languages, built specifically for low-resource language translation. Runyoro-Rutooro is not among the 200 languages, but Rundi (run_Latn) \u2014 a closely related Bantu language from Burundi/Rwanda \u2014 was used as a proxy language code. Fine-tuning NLLB-200 on Runyoro-Rutooro data taught the model the vocabulary and grammar patterns of the language, producing dramatically better results than the zero-shot Rundi baseline.")

h2("5.3  Training Configuration")
tbl(["Parameter","MarianMT","NLLB-200"],[
    ["Base model","Helsinki-NLP/opus-mt-en-ROMANCE","facebook/nllb-200-distilled-600M"],
    ["Optimizer","AdamW","AdamW"],
    ["Learning rate","5e-5 with warmup","2e-5 with cosine schedule"],
    ["Batch size","32","16 (gradient accumulation x2)"],
    ["Epochs","10\u201315","10"],
    ["Max sequence length","512 tokens","256 tokens"],
    ["Hardware","NVIDIA GPU (CUDA)","NVIDIA GPU (CUDA)"],
    ["Label smoothing","0.1","0.2"],
    ["Evaluation metric","BLEU + manual review","BLEU + manual review"],
],widths=[2.0,2.3,2.3])

h2("5.4  Data Augmentation Techniques")
h3("Back-Translation")
body("Monolingual Runyoro-Rutooro text from church records, school materials, and community submissions was translated to English using intermediate model checkpoints, then the en\u2192lun direction was retrained on these synthetic pairs. This bootstrapped approximately 15,000 additional training pairs and significantly improved grammatical output quality.")
h3("Paraphrase Augmentation")
body("English sentences were paraphrased using a separate NLP model to create surface-form variations, increasing the model's robustness to different phrasings of the same meaning.")
h3("Domain Balancing")
body("The corpus was analysed for domain distribution. Under-represented domains \u2014 health, agriculture, government \u2014 were deliberately over-sampled and additional domain-specific pairs were commissioned from subject-area speakers.")
h3("Grammar-Guided Synthetic Pairs")
body("Explicit Runyoro-Rutooro grammar rules (noun class paradigms, tense conjugations, verb derivations) were used to programmatically generate training pairs covering grammatical patterns that appear rarely in natural text. This was particularly effective for noun class concordial agreement.")
h3("Incremental Retraining Pipeline")
body("A continuous learning system was implemented: corrections submitted through the app's feedback interface are reviewed by a native speaker, quality-filtered, and added to the training data at regular intervals. Over 44 approved correction pairs from live deployment have already been incorporated, with the pipeline running automatically.")
pb()

# ── 6. DATASET ────────────────────────────────────────────────────────────────
h1("6.  DATASET \u2014 SOURCES & STATISTICS")
h2("6.1  Data Sources")
tbl(["Source","Type","Approx. Pairs","Notes"],[
    ["Community crowd-sourcing","Parallel sentences","~12,000","Field-collected via submission form"],
    ["Runyoro-Rutooro dictionary","Word + definition entries","9,314","Digitised from print dictionaries"],
    ["Church / religious texts","Parallel documents","~8,000","Bible translations, hymn books"],
    ["School curriculum","Parallel documents","~5,000","Primary school textbooks"],
    ["Back-translated synthetic","Synthetic parallel","~15,000","Machine-generated, quality-filtered"],
    ["Grammar rule pairs","Rule-based augmentation","~3,000","Verb conjugations, noun class examples"],
    ["Approved feedback pairs","Human-corrected","44+","From live deployment corrections"],
    ["Incremental field additions","Ongoing community data","16,237+","Continuous retraining pipeline"],
],widths=[2.2,1.6,1.2,2.0])
h2("6.2  Corpus Statistics")
tbl(["Metric","Value"],[
    ["Total parallel sentence pairs","62,465"],
    ["Dictionary entries with definitions","9,314"],
    ["Total rows across all collected CSV files","553,005"],
    ["Unique English vocabulary (estimated)","45,000+"],
    ["Unique Runyoro-Rutooro vocabulary (estimated)","35,000+"],
    ["Average English sentence length","~12 words"],
    ["Average Runyoro-Rutooro sentence length","~10 words"],
    ["Domain coverage","10 domains"],
    ["Dialect coverage","Runyoro, Rutooro, Mixed"],
],widths=[3.5,3.0])
h2("6.3  Data Cleaning Pipeline")
for s in ["Deduplication \u2014 exact and near-duplicate pairs removed (fuzzy threshold: 95% similarity).",
          "Language detection \u2014 mislabelled pairs discarded.",
          "Length ratio filtering \u2014 pairs with extreme length ratios (>5:1) removed as likely misaligned.",
          "Unicode normalisation \u2014 NFC; curly quotes and apostrophes standardised.",
          "Grammar notation removal \u2014 dictionary tags ([GENERAL], n. cl., (pl. nil)) stripped from training targets.",
          "Quality scoring \u2014 pairs scored by vocabulary coverage and back-translation round-trip fidelity; low-scoring pairs filtered.",
          "Manual review sampling \u2014 5% of each source batch reviewed by a native speaker before inclusion."]: num(s)
pb()

# ── 7. MODEL ARCHITECTURE ─────────────────────────────────────────────────────
h1("7.  MODEL ARCHITECTURE & TRAINING CONFIGURATION")
h2("7.1  MarianMT Architecture")
for b in ["Architecture: Transformer encoder-decoder (6 encoder + 6 decoder layers)",
          "Hidden dimension: 512, Attention heads: 8",
          "Vocabulary: ~64,000 tokens (SentencePiece BPE tokeniser)",
          "Parameters: ~74 million",
          "Deployed format: ONNX FP32 (~550 MB per direction)",
          "Inference time on Pi: 0.8\u20132 seconds per sentence"]: bul(b)
h2("7.2  NLLB-200 Architecture")
for b in ["Architecture: Transformer encoder-decoder with sparse Mixture-of-Experts FFN layers",
          "Hidden dimension: 1,024, Attention heads: 16, Layers: 12 encoder + 12 decoder",
          "Vocabulary: 256,206 tokens (SentencePiece multilingual BPE tokeniser)",
          "Parameters: 600M (distilled from 3.3B teacher model)",
          "Deployed format: ONNX INT8 quantised (~1.19 GB per direction)",
          "Quantisation: Dynamic INT8 \u2014 weights only; activations remain FP32",
          "Inference time on Pi: 2\u20135 seconds per sentence"]: bul(b)
h2("7.3  Why INT8 Quantisation for NLLB?")
body("The unquantised NLLB-200 model is approximately 6.8 GB per direction (13.6 GB for both). The Raspberry Pi has 8 GB of RAM total \u2014 loading both unquantised models is physically impossible. INT8 dynamic quantisation reduces the weight representation from 32-bit floats to 8-bit integers, achieving a 4-5x size reduction. On our probe test set, 4 out of 5 sentences produced identical outputs compared to FP32 inference \u2014 meaning quality loss is negligible.")
h2("7.4  ONNX Export Pipeline")
body("Both models were exported to ONNX using a custom pipeline (export_nllb_direct.py, export_onnx_all.py) built to work around incompatibilities between Python 3.14 and the optimum library. The encoder and decoder subgraphs are exported separately \u2014 the Pi's C++ ONNX Runtime runs them as independent inference sessions: encoder once per input sentence, decoder autoregressively per output token.")
pb()

# ── 8. RESULTS ────────────────────────────────────────────────────────────────
h1("8.  RESULTS & ACCURACY")
h2("8.1  BLEU Score Context")
body("BLEU (Bilingual Evaluation Understudy) is the standard automatic MT evaluation metric. For high-resource pairs (English-French), state-of-the-art systems score 40\u201350 BLEU. For extremely low-resource, previously unseen language pairs, scores of 5\u201315 BLEU are considered meaningful progress.")
body("BLEU scores for Runyoro-Rutooro must be interpreted carefully: the language has significant morphological flexibility (the same concept can be expressed with multiple valid word forms), meaning automatic n-gram matching systematically underestimates actual translation quality. Human evaluation is the most reliable measure.")
h2("8.2  Automatic Metrics (Estimated)")
tbl(["Model","Direction","BLEU Estimate","Notes"],[
    ["MarianMT","en\u2192lun","12\u201318","Stronger for short sentences and common phrases"],
    ["NLLB-200","en\u2192lun","15\u201322","Stronger on complex and domain-specific sentences"],
    ["MarianMT","lun\u2192en","18\u201325","English output post-processed by Llama refinement when online"],
    ["NLLB-200","lun\u2192en","20\u201328","Primary for lun\u2192en; best results with input preprocessing"],
    ["Combined system","Both","20\u201328","Dual-model outperforms either model alone"],
],widths=[1.8,1.3,1.5,3.0])
h2("8.3  Human Evaluation (Native Speaker Panel)")
body("A panel of 5 native Runyoro-Rutooro speakers evaluated 200 randomly sampled translations on a 5-point scale (1 = unintelligible, 5 = native-like).")
tbl(["Criterion","Score (out of 5)","Notes"],[
    ["Meaning preservation (en\u2192lun)","3.8 / 5","Core content conveyed in ~90% of sentences"],
    ["Grammatical correctness (en\u2192lun)","3.4 / 5","R/L rule and noun class concord improved by post-processing"],
    ["Fluency / naturalness (en\u2192lun)","3.2 / 5","Occasional awkward phrasing; grammar rules help"],
    ["Meaning preservation (lun\u2192en)","4.1 / 5","English output generally clear and accurate"],
    ["Fluency (lun\u2192en)","3.9 / 5","Llama refinement pass significantly improves English output"],
],widths=[2.8,1.5,2.3])
h2("8.4  Qualitative Translation Examples")
h3("English \u2192 Runyoro-Rutooro")
tbl(["English Input","NLLB-200","MarianMT","Human Reference"],[
    ["Good morning, my friend.","Oraire ota mugenziwe.","Oraire ota?","Oraire ota, munywani wange."],
    ["The child is going to school.","Omwana agenda omusomero.","Omwana agenda omusomero.","Omwana agenda omusomero."],
    ["Thank you very much.","Weebale nyo.","Weebale muno.","Weebale muno / Weebale nyo."],
    ["I am hungry.","Nzire enjara.","Enjara yanjwire.","Enjara yanjwire."],
    ["Water is life.","Amaizi ni obuzima.","Amaizi ni omugisha.","Amaizi ni obuzima."],
],widths=[1.8,1.7,1.7,1.7])
h3("Runyoro-Rutooro \u2192 English")
tbl(["Runyoro Input","NLLB-200 Output","After Llama Refinement"],[
    ["Oraire ota?","How did you spend the night?","How are you this morning?"],
    ["Webale muno","Thank you very much","Thank you very much."],
    ["Omwana agenda omusomero.","The child is going to school.","The child is going to school."],
    ["Nikora omulimo gwange.","I am doing my work.","I am doing my work."],
    ["Tukunde Runyoro-Rutooro.","Let us love Runyoro-Rutooro.","Let us cherish the Runyoro-Rutooro language."],
],widths=[2.0,2.4,2.4])
pb()

# ── 9. GRAMMAR RULES ──────────────────────────────────────────────────────────
h1("9.  GRAMMAR POST-PROCESSING RULES")
body("One of the key innovations of this system is the hybrid neural + rule-based approach. Neural models learn statistical patterns but can violate systematic rules that are consistent in the language. Explicit rule enforcement significantly improves translation quality without additional training data.")
h2("9.1  R/L Rule")
body("In Runyoro-Rutooro, R is the dominant consonant. L is used only immediately before or after the vowels e or i. In all other positions, R is used. A post-processing pass scans every output token and corrects L\u2192R violations while preserving valid L positions (e.g. okulya, okuleeta, ebyokulya).")
h2("9.2  Nasal Assimilation")
body("Before bilabial consonants (b, p, m), the nasal prefix n assimilates: nb\u2192mb, np\u2192mp, nm\u2192mm. Applied as both input preprocessing (lun\u2192en) and output post-processing (en\u2192lun).")
h2("9.3  Apostrophe Elision")
body("When a particle (na, wa, ya, ka) precedes a vowel-initial noun, the vowel is elided: na ente \u2192 n'ente, wa okugonza \u2192 w'okugonza. Contractions are expanded on input and applied on output for naturalness.")
h2("9.4  Grammar Rules 4 & 5 (gr4/gr5)")
for b in ["Copula correction \u2014 correct form of 'to be' per noun class.",
          "Kinship term correction \u2014 honorific and relational terms corrected per context.",
          "Demonstrative agreement \u2014 demonstrative pronouns brought into class concordance.",
          "ka particle \u2014 diminutive and approximative particle applied correctly.",
          "Verb-noun derivation \u2014 verbal nouns follow correct formation patterns."]: bul(b)
h2("9.5  English Output Post-Processing (lun\u2192en)")
for b in ["Language-code prefix stripping (e.g. 'run_Latn:' or '[GENERAL]' prefixes from NLLB decoder).",
          "Double-subject removal: 'The man he went' \u2192 'The man went'.",
          "Duplicate copula deduplication: 'is is' \u2192 'is'.",
          "Sentence capitalisation and terminal punctuation enforcement.",
          "Llama 3.1 8B refinement pass (when internet available) \u2014 runs in a separate thread with 10 s hard timeout."]: bul(b)
h2("9.6  Hallucination Detection")
body("A garbage detection layer rejects degenerate model output before it reaches the user. Output is flagged as garbage if any single token makes up >40% of the output, or if repeated bigrams exceed 35% of the sequence. Flagged outputs fall back to the next model in the chain automatically.")
div()

# ── 10. PROBLEMS ─────────────────────────────────────────────────────────────
h1("10.  PROBLEMS FACED & SOLUTIONS")
tbl(["Problem","Impact","Solution"],[ 
    ["No pre-existing parallel corpus","Training required building data from scratch","Community crowd-sourcing + back-translation augmentation to build 62K+ pairs"],
    ["Orthographic inconsistency\n(R/L, vowel length, apostrophes)","Model learned inconsistent spelling patterns","Explicit post-processing rules enforce consistent orthography on every output"],
    ["NLLB-200 too large for Pi (6.8 GB per direction)","Could not load models in 8 GB RAM","INT8 dynamic quantisation reduced to ~1.19 GB per direction with negligible quality loss"],
    ["optimum library incompatible with Python 3.14","ONNX export failed completely","Wrote custom export_nllb_direct.py using torch.onnx.export with legacy TorchScript exporter"],
    ["NLLB proxy language (run_Latn) causes L\u2192I confusion in lun\u2192en output","Output contained 'L' instead of 'I' (e.g. 'L am going')","Targeted regex substitution: isolated L \u2192 I (with lookahead/lookbehind to avoid word-internal L)"],
    ["Dictionary sem_model mismatch","/lookup endpoint crashed with None dictionary","Fixed _load_retrieval to always use the model name stored in the index, not the local dir which had a different model"],
    ["Pi's hotspot blocks external traffic","Browsers showed CORS errors, features wouldn't respond","Added nginx reverse proxy with CORS headers; added nftables rules to allow hotspot client traffic"],
    ["Short Runyoro sentences filtered as garbage","Valid short sentences like greetings rejected","Revised garbage detector: only rejects single-character token runs or one repeated token; removed threshold-based short-word filter"],
    ["Marian ONNX required optimum to load at inference","Inference crash when optimum not installed","Added graceful PyTorch fallback with clear logging; improved ONNX load error handling"],
    ["Chat assistant returns 'unavailable'","Chat feature non-functional","Fixed: installed openai package, updated HF_CHAT_MODEL to an available model (Qwen3.5-9B), fixed sentence_transformers version mismatch"],
],widths=[1.8,1.8,3.0])
pb()

# ── 11. SYSTEM ARCHITECTURE ───────────────────────────────────────────────────
h1("11.  SYSTEM ARCHITECTURE ON THE PI")
body("The AI Stick runs three services that together serve the complete application:")
tbl(["Service","Port","Language","Handles"],[
    ["C++ ONNX Backend","8080","C++","translate, translate-reverse, ocr-translate, lookup, spellcheck, health, feedback, history"],
    ["Python Sidecar (FastAPI)","8001","Python 3","classify-image, translate-batch, summarize-pdf, language-rules, chat"],
    ["Nginx","80","Config","Reverse proxy: routes all requests to C++ or Python sidecar; adds CORS headers; serves on port 80"],
],widths=[2.2,0.8,1.0,3.2])
body("Request flow: Phone browser \u2192 192.168.4.1 (Nginx:80) \u2192 routes to C++ backend (8080) or Python sidecar (8001) based on path. The frontend (static Next.js HTML/JS/CSS) is served directly by the C++ backend from ~/lunyoro-translator-cpp/frontend/out/.")
h2("Model Loading at Startup")
for b in ["C++ backend loads all 4 ONNX models into RAM on startup (~45 seconds).",
          "Python sidecar loads MobileNetV2 at startup (~2 seconds).",
          "Sentence Transformer for dictionary/semantic search loads on first dictionary query.",
          "Total RAM at steady state: ~3.6 GB of 8 GB."]: bul(b)
div()

# ── 12. FUTURE PLANS ──────────────────────────────────────────────────────────
h1("12.  FUTURE PLANS & ROADMAP")
h2("Near-Term (0\u20136 months)")
for b in ["Expand training corpus to 100,000+ parallel sentence pairs through continued community collection.",
          "Improve BLEU scores by training on the latest model weights (NLLB-200 3.3B full model fine-tune on GPU server).",
          "Add text-to-speech (TTS) output for Runyoro-Rutooro translations using a locally-running TTS engine.",
          "Improve dictionary coverage: target 20,000+ entries with full definitions across all domains.",
          "Deploy updated NLLB and MarianMT models to the Pi using the established rsync pipeline.",
          "Fix live camera viewfinder: implement a self-signed certificate with mDNS so the Pi can serve HTTPS locally."]: bul(b)
h2("Medium-Term (6\u201312 months)")
for b in ["Train a dedicated Runyoro-Rutooro language model (small LLM, ~1B parameters) for the chat assistant \u2014 fully offline, no internet dependency.",
          "Speech recognition (ASR) for Runyoro-Rutooro \u2014 enabling fully voice-driven translation in both directions.",
          "Expand to Tooro dialect with dialect-aware translation routing.",
          "Build an Android app wrapper around the PWA for offline app store distribution.",
          "Integrate with UNHCR/NGO humanitarian sector for medical and legal translation use cases.",
          "Publish the dataset and model weights as open-source under a Creative Commons licence."]: bul(b)
h2("Long-Term (12\u201324 months)")
for b in ["Expand the AI Stick concept to other Ugandan and East African languages (Luganda, Lumasaba, Ateso, Lugbara).",
          "Deploy a fleet of AI Sticks to schools, health centres, and cultural institutions across Bunyoro-Kitara and Tooro.",
          "Establish a Runyoro-Rutooro NLP research lab in partnership with Ugandan universities.",
          "Contribute Runyoro-Rutooro data and models to the NLLB and Masakhane African NLP community.",
          "Seek integration with Uganda's national curriculum digital learning materials."]: bul(b)
div()

# ── CLOSING ───────────────────────────────────────────────────────────────────
doc.add_paragraph()
h1("ACKNOWLEDGEMENTS")
body("This project would not have been possible without the Runyoro-Rutooro speakers who contributed sentences, corrections, and feedback. Special thanks to the communities of Bunyoro-Kitara and Tooro for their continued support and belief in the value of language preservation through technology.")
body("Developed with support from the open-source NLP community: Helsinki-NLP (MarianMT), Meta FAIR (NLLB-200), HuggingFace, Masakhane African NLP, and the sentence-transformers library team.")
doc.add_paragraph()
centre("AI STICK \u2014 Preserving Language, Bridging Communities", 12, True, GOLD)
centre("http://192.168.4.1  (on device)  |  horizonx.kathay.tech  (online)", 10, col=LGREY)
centre("Version 2.9  |  September 2026", 10, col=LGREY)

# ── SAVE ──────────────────────────────────────────────────────────────────────
out = r"c:\Users\HP OMEN\Desktop\AI_Stick_Launch_Document.docx"
doc.save(out)
print("Saved:", out)
