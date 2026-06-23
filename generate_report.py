import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # Color definitions
        primary_color = colors.HexColor("#0F766E")  # Deep Teal
        border_color = colors.HexColor("#CBD5E1")   # Muted Grey/Blue
        text_color = colors.HexColor("#64748B")     # Cool Slate
        
        # Header (Only on Page 2, Page 1 has the main banner)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8.5)
            self.setFillColor(primary_color)
            self.drawString(54, 752, "OUTREACH NODE — CUSTOM COLD EMAILER")
            
            self.setFont("Helvetica", 8.5)
            self.setFillColor(text_color)
            self.drawRightString(558, 752, "Architecture & Implementation Guide")
            
            self.setStrokeColor(border_color)
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)
        
        # Footer (On all pages)
        self.setStrokeColor(border_color)
        self.setLineWidth(0.5)
        self.line(54, 55, 558, 55)
        
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))
        self.drawString(54, 40, "Confidential — UAV Lab Internship Project")
        
        self.setFont("Helvetica", 8)
        self.setFillColor(text_color)
        self.drawCentredString(306, 40, "Developed by Mughees Tayyab")
        
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 40, page_text)
        
        self.restoreState()

def create_project_pdf(filename="Outreach_Node_Project_Documentation.pdf"):
    # Target printable area: 504 pt width (8.5 * 72 - 108 pt margins)
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Paragraph Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.white,
        alignment=1  # Centered
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#CCFBF1'),
        alignment=1  # Centered
    )
    
    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#475569'),
        alignment=1,  # Centered
        spaceAfter=12
    )
    
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#0F766E'),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9,
        leading=12.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )
    
    bullet_style = ParagraphStyle(
        'DocBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#334155'),
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3
    )
    
    header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#334155')
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1E293B')
    )

    story = []
    
    # ═══════════════════════════════════════════════════════════════
    # PAGE 1: TITLE & CORE CAPABILITIES & SPECIFICATIONS
    # ═══════════════════════════════════════════════════════════════
    
    # Title Banner Table
    banner_data = [
        [Paragraph("OUTREACH NODE — CUSTOM COLD EMAILER", title_style)],
        [Paragraph("Multi-Agent AI Outreach Orchestrator & Voicemail Synthesizer", subtitle_style)]
    ]
    banner_table = Table(banner_data, colWidths=[504])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#0F766E')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,0), 14),
        ('BOTTOMPADDING', (0,-1), (-1,-1), 14),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 8))
    
    # Meta Block
    story.append(Paragraph("UAV Lab Internship Capstone Project &bull; Developer: Mughees Tayyab &bull; Status: Production Release", meta_style))
    
    # Executive Summary
    story.append(Paragraph("Executive Summary & Project Overview", h1_style))
    summary_text = (
        "<b>Outreach Node (GreenFactor)</b> is a state-of-the-art, multi-agent cold email campaign manager "
        "engineered to automate personalized outbound prospecting. The project solves the key limitations "
        "of traditional cold emailing—namely, static templates, manual company research, and high bounce rates—by "
        "orchestrating a structured sequence of AI agents. Each agent operates with specific roles, performing keyless "
        "scraping, company profiling, copywriting, and recursive critique loops. Additionally, the system features "
        "Google Text-to-Speech (gTTS) integration to automatically synthesize customized audio voicemail pitches, and an "
        "SMTP email dispatcher to support one-click campaign execution. The interface utilizes a premium dark glassmorphism "
        "design system to visualize execution pipelines and results."
    )
    story.append(Paragraph(summary_text, body_style))
    
    # Key Capabilities & Features
    story.append(Paragraph("Key System Capabilities", h1_style))
    
    features = [
        "<b>Social Media Prospecting:</b> DuckDuckGo-powered keyless lookups discover professional summaries and organizational titles dynamically without relying on expensive, rate-limited LinkedIn APIs.",
        "<b>Company Context Ingestion:</b> Synthesizes strategist briefs by scraping Wikipedia and executing targeted search queries to extract recent news, core offerings, and strategic pain points.",
        "<b>Personalized Copywriting:</b> Generates custom subject lines and body copy tailored to specific target alignment hooks, brand tones, and sender profiles.",
        "<b>Self-Correcting Critique Loop:</b> The proofreader agent evaluates drafts against strict alignment and accuracy criteria. If a draft scores below 7/10, the proofreader generates feedback, prompting the copywriter to revise up to 3 times.",
        "<b>Voicemail Synthesis (gTTS):</b> Automatically generates 100% free personalized MP3 voice scripts referencing the prospect's company and sender context, eliminating the need for paid speech synthesis API keys.",
        "<b>SMTP Dispatcher & Excel Reporting:</b> Supports direct campaign dispatching via SMTP (e.g., Gmail App Passwords) and compiles a fully formatted, color-coded Excel spreadsheet output mapping campaign progress."
    ]
    
    for f in features:
        story.append(Paragraph(f"&bull; {f}", bullet_style))
        
    story.append(Spacer(1, 4))
    
    # Technical Specifications Table
    story.append(Paragraph("Technical Infrastructure & Requirements", h1_style))
    
    req_headers = [
        Paragraph("Category", header_style),
        Paragraph("Dependencies / Technologies", header_style),
        Paragraph("System Role", header_style)
    ]
    
    req_rows = [
        [
            Paragraph("Core Framework", table_cell_bold),
            Paragraph("Python 3.10+, Flask 3.1.1, python-dotenv", table_cell_style),
            Paragraph("Handles backend server operations, configuration, and routing.", table_cell_style)
        ],
        [
            Paragraph("AI Client Layer", table_cell_bold),
            Paragraph("litellm, google-genai, openai", table_cell_style),
            Paragraph("Provides a unified API client wrapping model invocation (gateway-claude-opus-4-8).", table_cell_style)
        ],
        [
            Paragraph("Intelligence Tools", table_cell_bold),
            Paragraph("duckduckgo-search, requests, LXML", table_cell_style),
            Paragraph("Executes search scraping and extracts text from Wikipedia pages.", table_cell_style)
        ],
        [
            Paragraph("Data Processing", table_cell_bold),
            Paragraph("openpyxl, pandas, PyPDF2, python-docx", table_cell_style),
            Paragraph("Parses incoming context PDFs/DOCX and outputs styled Excel logs.", table_cell_style)
        ],
        [
            Paragraph("Media & Dispatch", table_cell_bold),
            Paragraph("gTTS 2.5.4, smtplib (SMTP)", table_cell_style),
            Paragraph("Renders personalized MP3 voicemail audio and dispatches emails.", table_cell_style)
        ]
    ]
    
    table_data = [req_headers] + req_rows
    # Column widths: 108 pt, 200 pt, 196 pt = 504 pt
    tech_table = Table(table_data, colWidths=[108, 200, 196])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F766E')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#F8FAFC'), colors.HexColor('#FFFFFF')]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    
    story.append(tech_table)
    
    # Page Break to ensure exactly 2 pages
    story.append(PageBreak())
    
    # ═══════════════════════════════════════════════════════════════
    # PAGE 2: ARCHITECTURE & IMPLEMENTATION DETAILS
    # ═══════════════════════════════════════════════════════════════
    
    story.append(Paragraph("System Architecture & Multi-Agent Pipeline", h1_style))
    
    arch_intro = (
        "The core logic of Outreach Node is encapsulated in the <code>Orchestrator</code> class, "
        "which runs each campaign asynchronously in dedicated background threads to prevent UI-blocking. "
        "A centralized state management engine (<code>StateManager</code>) records execution logs as JSON records "
        "and handles concurrent pipeline progress updates in real-time."
    )
    story.append(Paragraph(arch_intro, body_style))
    
    # Stepper details
    story.append(Paragraph("Sequential Execution Sequence", h2_style))
    
    steps = [
        "<b>Stage 0: Orchestrator Agent (Analysis):</b> Before querying individual prospects, the Orchestrator Agent analyzes the user's custom campaign prompt and attached reference documents. It generates a structured <code>research_plan</code> defining target keywords, LinkedIn/Web search query templates, and copy requirements.",
        "<b>Stage 1: Prospecting Agent (Discovery):</b> Extracts the target name and company from the input sheet, running keyless web queries to output a high-level summary of the prospect's professional background.",
        "<b>Stage 2: LinkedIn Agent (Intelligence):</b> Guided by the <code>research_plan</code>, it performs targeted searches to discover additional professional insights, target milestones, and executive context.",
        "<b>Stage 3: Context Agent (Company Profiling):</b> Gathers deep corporate details by combining Wikipedia scrapes with DuckDuckGo searches, mapping the company's core services, recent news, and specific pain points.",
        "<b>Stage 4: Copywriter Agent (Draft Generation):</b> Synthesizes all gathered information (prospect summary, corporate pain points, sender credentials, tone settings, and campaign goals) to draft a hyper-personalized email subject and body.",
        "<b>Stage 5: Proofreader Agent (Critique & Self-Correction):</b> Analyzes the draft against ground truths and alignment guidelines, scoring the copy on Relevance, Tone, Personalization, and Accuracy. If the score is &lt; 7, it generates specific critiques and returns execution to the Copywriter for revision (capped at 3 retries).",
        "<b>Stage 6: Output Compilation (Excel & TTS):</b> On final draft approval, the system updates the campaign log, runs gTTS to generate the MP3 voicemail file, and writes all records to a formatted Excel file."
    ]
    
    for s in steps:
        story.append(Paragraph(s, bullet_style))
        
    story.append(Spacer(1, 4))
    
    # Implementation Architecture Table
    story.append(Paragraph("Software Architecture & Directory Blueprint", h1_style))
    
    arch_headers = [
        Paragraph("Directory / File", header_style),
        Paragraph("Code Files", header_style),
        Paragraph("Operational Implementation & Design", header_style)
    ]
    
    arch_rows = [
        [
            Paragraph("agents/", table_cell_bold),
            Paragraph("orchestrator_agent.py, context_agent.py, copywriter_agent.py, proofreader_agent.py", table_cell_style),
            Paragraph("LLM agents implementing tailored prompts, JSON output formatting, and recursive validation loops.", table_cell_style)
        ],
        [
            Paragraph("middleware/", table_cell_bold),
            Paragraph("orchestrator.py, state_manager.py, ai_client.py", table_cell_style),
            Paragraph("Campaign orchestration thread managers, JSON state managers, and central LLM connection middleware.", table_cell_style)
        ],
        [
            Paragraph("tools/", table_cell_bold),
            Paragraph("search_tool.py, excel_tool.py, tts_tool.py, document_tool.py, email_tool.py", table_cell_style),
            Paragraph("Underlying functional APIs for web scraping, Excel openpyxl parsing, TTS audio rendering, and SMTP emailing.", table_cell_style)
        ],
        [
            Paragraph("templates/ & static/", table_cell_bold),
            Paragraph("dashboard.html, pipeline.html, results.html, index.css", table_cell_style),
            Paragraph("Dark glassmorphism frontend layout, stepper trackers, audio players, and inline copy editors.", table_cell_style)
        ]
    ]
    
    arch_table_data = [arch_headers] + arch_rows
    # Column widths: 90 pt, 174 pt, 240 pt = 504 pt
    arch_table = Table(arch_table_data, colWidths=[90, 174, 240])
    arch_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F766E')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#F8FAFC'), colors.HexColor('#FFFFFF')]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    
    story.append(arch_table)
    story.append(Spacer(1, 4))
    
    # Running the Project
    story.append(Paragraph("Verification & Deployment", h1_style))
    deployment_text = (
        "<b>1. Setup & Launch:</b> Initialize python environment: <code>python -m venv venv</code>, "
        "activate it, and run <code>pip install -r requirements.txt</code>. Copy <code>.env.example</code> to "
        "<code>.env</code> and populate <code>API_KEY</code> and optional SMTP settings. Launch via "
        "<code>python app.py</code>.<br/>"
        "<b>2. Automated Tests:</b> Run test suites locally using: <code>pytest tests/ -v</code>. "
        "Tests validate the Mock SMTP dispatcher, state logging serialization, Excel parsers, and individual agent logic."
    )
    story.append(Paragraph(deployment_text, body_style))
    
    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)

if __name__ == "__main__":
    create_project_pdf()
    print("PDF Generation complete.")
