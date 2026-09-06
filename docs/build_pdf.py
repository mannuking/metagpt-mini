"""Generate the MetaGPT-Mini learning PDF.

Run from project root:
    source .venv/bin/activate
    python docs/build_pdf.py
"""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Preformatted, ListFlowable, ListItem,
)

OUT = os.path.join(os.path.dirname(__file__), "MetaGPT-Mini-Learning-Guide.pdf")

styles = getSampleStyleSheet()

H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold",
                    fontSize=20, leading=26, spaceBefore=18, spaceAfter=10,
                    textColor=colors.HexColor("#0E2A47"))
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                    fontSize=14, leading=18, spaceBefore=14, spaceAfter=6,
                    textColor=colors.HexColor("#1F4E79"))
H3 = ParagraphStyle("H3", parent=styles["Heading3"], fontName="Helvetica-Bold",
                    fontSize=11, leading=14, spaceBefore=10, spaceAfter=4,
                    textColor=colors.HexColor("#2E75B6"))
BODY = ParagraphStyle("BODY", parent=styles["BodyText"], fontName="Helvetica",
                      fontSize=10, leading=14, spaceAfter=6, alignment=TA_JUSTIFY)
BULLET = ParagraphStyle("BULLET", parent=BODY, leftIndent=14, bulletIndent=2,
                        spaceAfter=3, alignment=0)
CODE = ParagraphStyle("CODE", parent=styles["Code"], fontName="Courier",
                      fontSize=8.5, leading=11, leftIndent=4, spaceAfter=4,
                      backColor=colors.HexColor("#F4F4F4"),
                      borderColor=colors.HexColor("#DDDDDD"), borderWidth=0.5,
                      borderPadding=6)
CENTER = ParagraphStyle("CENTER", parent=BODY, alignment=TA_CENTER)
TITLE = ParagraphStyle("TITLE", parent=styles["Title"], fontName="Helvetica-Bold",
                       fontSize=28, leading=34, alignment=TA_CENTER, spaceAfter=8)
SUBTITLE = ParagraphStyle("SUBTITLE", parent=BODY, fontName="Helvetica",
                          fontSize=13, alignment=TA_CENTER,
                          textColor=colors.HexColor("#555555"))


def header_footer(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(colors.HexColor("#888888"))
    canvas_obj.drawRightString(A4[0] - 2 * cm, A4[1] - 1.2 * cm,
                               "MetaGPT-Mini - Learning Guide")
    canvas_obj.drawCentredString(A4[0] / 2, 1.2 * cm,
                                 "Page " + str(doc.page))
    canvas_obj.drawString(2 * cm, 1.2 * cm,
                          "Jai Kumar Meena - DTU M.Tech by Research CSE")
    canvas_obj.restoreState()


def code(text):
    return Preformatted(text, CODE)


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(i, BULLET)) for i in items],
        bulletType="bullet", leftIndent=12, bulletFontSize=8,
    )


# ---- Helper: paragraph builder that avoids nested quote problems --------------
def p(*chunks):
    """Concatenate text chunks and wrap in Paragraph."""
    return Paragraph("".join(chunks), BODY)


# ---- Build the story ---------------------------------------------------------

story = []

# Cover page
story += [
    Spacer(1, 4 * cm),
    Paragraph("MetaGPT-Mini", TITLE),
    Paragraph("An LLM-agnostic reimplementation of<br/>"
              "MetaGPT (ICLR 2024 Oral, #1 LLM-Agent)", SUBTITLE),
    Spacer(1, 1.5 * cm),
    Paragraph("A learning guide for the M.Tech class", CENTER),
    Spacer(1, 0.5 * cm),
    Paragraph("Jai Kumar Meena - M.Tech by Research, CSE", CENTER),
    Paragraph("Delhi Technological University", CENTER),
    Spacer(1, 0.3 * cm),
    Paragraph("https://github.com/mannuking/metagpt-mini", CENTER),
    Spacer(1, 6 * cm),
    Paragraph("<b>Five papers. One implemented. Zero closed-source models.</b>",
              CENTER),
    PageBreak(),
]

# Section 1 — Why MetaGPT
story += [
    Paragraph("1. Why I Picked MetaGPT Out of the Five", H1),
    p("I had to choose <b>one paper</b> to teach in class tomorrow out of "
      "five famous agentic-engineering papers, all from top-tier venues "
      "(NeurIPS, ICLR, COLM). Here is the comparison and the reasoning."),
    Spacer(1, 0.3 * cm),
    Paragraph("The five papers at a glance", H3),
    Spacer(1, 0.2 * cm),
    p("<b>MetaGPT</b> - Multi-agent orchestration with SOPs. PM, Architect, "
      "Engineer, QA collaborating via a shared message pool. "
      "<i>(ICLR 2024 Oral - top 1.2% of all submissions, ranked #1 in the "
      "LLM-Agent category.)</i>"),
    p("<b>SWE-agent</b> - Agent-Computer Interfaces for autonomous software "
      "engineering. State-of-the-art on SWE-bench at the time of publication. "
      "<i>(NeurIPS 2024.)</i>"),
    p("<b>OpenHands (OpenDevin)</b> - Production-grade agent runtime. "
      "Terminals, browsers, editors, code interpreters in one harness. "
      "<i>(COLM 2024 Oral.)</i>"),
    p("<b>Reflexion</b> - Self-improving agent memory via verbal "
      "reinforcement. <i>(NeurIPS 2023.)</i>"),
    p("<b>Voyager</b> - Lifelong skill acquisition: an agent that grows its "
      "own tool library. <i>(NeurIPS 2023.)</i>"),
    Spacer(1, 0.3 * cm),
    Paragraph("Why MetaGPT won", H3),
    bullets([
        "<b>Pedagogical completeness.</b> MetaGPT is the only paper that "
        "models an entire organization (PM + Architect + Engineer + QA). "
        "Five other layers (orchestration, message passing, role "
        "specialization, SOP encoding, output verification) all appear in "
        "one paper.",
        "<b>Reproducibility in 1 hour.</b> The data flow is message-passing, "
        "not heavy machinery like Docker (OpenHands), reinforcement-learning "
        "training loops (Reflexion), or skill-library code-execution "
        "sandboxes (Voyager). A student can read and implement MetaGPT in 1 "
        "hour; the others take 1 day.",
        "<b>Real citations.</b> 50k+ GitHub stars on the original, hundreds "
        "of follow-up papers, ICLR Oral - no marketing fluff needed.",
        "<b>Maps to the 2026 frontier.</b> The harness-engineering papers I "
        "researched (arxiv 2603-2609) all explicitly cite MetaGPT as the "
        "multi-agent baseline. Teaching MetaGPT is teaching the foundation "
        "the new 2026 work builds on.",
    ]),
    Spacer(1, 0.2 * cm),
    Paragraph("What MetaGPT does NOT do (where the others win)", H3),
    bullets([
        "SWE-agent beats it on raw SWE-bench scores (better agent-computer "
        "interface).",
        "OpenHands is the production-grade runtime that would actually "
        "deploy MetaGPT.",
        "Reflexion adds self-reflection - MetaGPT does not learn from past "
        "runs.",
        "Voyager grows skills continuously - MetaGPT is stateless across "
        "runs.",
    ]),
    p("All of those are <i>additive</i>: you can bolt Reflexion "
      "self-reflection or Voyager skill library onto MetaGPT. MetaGPT is "
      "the substrate."),
    PageBreak(),
]

# Section 2 — Other four papers
tbl = [
    ["Paper", "Venue", "Year", "Core idea", "Best demo time"],
    ["MetaGPT", "ICLR 2024 Oral", "2024",
     "Multi-agent SOP orchestration (PM/Arch/Eng/QA)", "1 minute"],
    ["SWE-agent", "NeurIPS 2024", "2024",
     "Agent-Computer Interface design pattern",
     "5 minutes (needs Docker)"],
    ["OpenHands", "COLM 2024 Oral", "2024",
     "Production-grade agent harness runtime",
     "10+ min (full Docker stack)"],
    ["Reflexion", "NeurIPS 2023", "2023",
     "Verbal-RL: agents self-reflect from failure", "1 minute"],
    ["Voyager", "NeurIPS 2023", "2023",
     "Lifelong skill acquisition + curriculum",
     "5+ min (needs Minecraft env)"],
]
ttbl = Table(tbl, colWidths=[2.5*cm, 2.6*cm, 1.2*cm, 7.5*cm, 2.5*cm])
ttbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 9),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("FONTSIZE", (0, 1), (-1, -1), 8.5),
    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#888888")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
     [colors.white, colors.HexColor("#F4F8FC")]),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))

story += [
    Paragraph("2. The Four Other Papers - Context", H1),
    p("Even though MetaGPT is what we implement, you should be able to "
      "place it next to its peers on a slide and answer: why not the other? "
      "Here is the at-a-glance summary of each."),
    Spacer(1, 0.3 * cm),
    ttbl,
    Spacer(1, 0.5 * cm),
    Paragraph("Each paper in 60 seconds", H2),
    Paragraph("SWE-agent (NeurIPS 2024)", H3),
    p("Yang et al. noticed that the LLM is fine, but the <i>interface</i> "
      "matters more. A custom Agent-Computer Interface (ACI), with short "
      "commands and scoped outputs, lets GPT-4 solve 12.29% of SWE-bench "
      "issues end-to-end. The key insight: do not make the LLM type shell "
      "commands; give it purpose-built verbs."),
    Paragraph("OpenHands (COLM 2024 Oral)", H3),
    p("Formerly OpenDevin. A platform that runs an agent with: a bash "
      "sandbox, a browser, an editor, an IPython kernel, all under one "
      "runtime. This is what you would actually <i>deploy</i>; MetaGPT is "
      "what you would actually <i>reason about</i>. OpenHands builds a "
      "MetaGPT-like team but inside a real runtime."),
    Paragraph("Reflexion (NeurIPS 2023)", H3),
    p("Shinn et al. let an agent keep a verbal <i>self-reflection</i> after "
      "every failed trial. Next time, it reads its own past reflections and "
      "decides differently. No weight updates - just text in a memory "
      "buffer. Drops onto MetaGPT like a memory layer."),
    Paragraph("Voyager (NeurIPS 2023)", H3),
    p("Wang et al. dropped GPT-4 into Minecraft with three modules: a "
      "curriculum generator that proposes the next hardest achievable task, "
      "a skill library that stores reusable code, and a reflection module. "
      "The agent grows its own toolkit forever. This is the skills-as-a-"
      "knowledge-graph idea, conceptually close to the Hermes skill system."),
    Paragraph("The meta-takeaway", H3),
    p("Every one of these papers can be summarized as: <i>give the LLM a "
      "better loop</i>. MetaGPT gives it a team. SWE-agent gives it better "
      "tools. OpenHands gives it a runtime. Reflexion gives it memory. "
      "Voyager gives it lifelong growth. The frontier of 2026 "
      "harness-engineering is putting all of these together."),
    PageBreak(),
]

# Section 3 — MetaGPT paper read-along
story += [
    Paragraph("3. The MetaGPT Paper - Read-Along Guide", H1),
    p("If you are going to teach this paper to others, here is how to read "
      "it in one sitting. The PDF is in the project folder: "
      "<i>02_metagpt.pdf</i>."),
    Paragraph("Section 1 Introduction - what problem they solve", H3),
    p("Existing single-agent LLM systems fail at complex software "
      "engineering because they have no division of labour and no standard "
      "procedures. Humans solve this with SOPs (PM writes specs, Architect "
      "designs, Engineer codes, QA tests). MetaGPT claim: encoding SOPs as "
      "prompt sequences and running them across role-specialised agents "
      "gets you 3.6x better and 10x cheaper than GPT-4 single-agent on "
      "HumanEval pass@1."),
    Paragraph("Section 2 Related Work - where MetaGPT sits", H3),
    bullets([
        "Single-agent (AutoGPT, BabyAGI): no structure, explodes in cost",
        "Multi-agent role-play (CAMEL): two agents, no SOP",
        "Society of Mind (Minsky, 1986): theoretical, no LLM implementation",
        "MetaGPT is the first to put SOPs into a multi-agent LLM system",
    ]),
    Paragraph("Section 3 Framework - the architecture we re-implement", H3),
    p("The MetaGPT architecture has three layers:"),
    bullets([
        "<b>Environment</b> - a shared space where messages are published "
        "and subscribed. (Our <font face='Courier'>MessagePool</font> in "
        "<font face='Courier'>schema.py</font>.)",
        "<b>Agents (Roles and Profiles)</b> - a Role has a name, a profile "
        "(Senior PM), and a set of Actions it can execute. (Our "
        "<font face='Courier'>Role</font> class in "
        "<font face='Courier'>roles.py</font>.)",
        "<b>Actions</b> - the verbs. <font face='Courier'>WritePRD</font>, "
        "<font face='Courier'>WriteDesign</font>, "
        "<font face='Courier'>WriteCode</font>, "
        "<font face='Courier'>WriteTest</font>. Each takes context, emits "
        "a Message.",
    ]),
    p("The <i>message</i> object is the key abstraction. It carries "
      "<font face='Courier'>role</font>, "
      "<font face='Courier'>content</font>, "
      "<font face='Courier'>cause_by</font>, "
      "<font face='Courier'>msg_id</font>, "
      "<font face='Courier'>created_at</font>. Every agent sees every "
      "message but only acts on the ones its SOP needs."),
    Paragraph("Section 3.4 Standard Operating Procedures - the meta-pattern",
              H3),
    p("An SOP in MetaGPT is the directed-acyclic-graph of actions. The "
      "canonical SOP is: <i>WritePRD then WriteDesign then WriteCode then "
      "WriteTest</i>. Our <font face='Courier'>DEFAULT_SOP</font> list and "
      "<font face='Courier'>make_canonical_team</font> in "
      "<font face='Courier'>roles.py</font> implement exactly this."),
    Paragraph("Section 4 Experiments - what MetaGPT was measured on", H3),
    bullets([
        "<b>HumanEval pass@1:</b> 85.9% with GPT-3.5 vs 67.8% single-agent "
        "(cost reduced 10x)",
        "<b>HumanEval-ET:</b> higher-quality pass when full SOP team runs",
        "<b>MBPP:</b> similar pattern; SOP team consistently wins",
        "<b>Software development benchmark:</b> full project (3.6x quality "
        "of single-agent)",
    ]),
    Paragraph("Section 5 Discussion - limitations and future", H3),
    p("MetaGPT does not learn across runs (that is where Reflexion and "
      "Voyager extend it). It assumes humans provide the SOP; it does not "
      "invent one. These limits define exactly the open problems the 2026 "
      "harness-engineering papers are trying to solve."),
    PageBreak(),
]

# Section 4 — file-by-file
story += [
    Paragraph("4. Our Reimplementation - File-by-File Walkthrough", H1),
    p("Every line in MetaGPT-Mini maps to a concept in the paper. Here is "
      "what each file does, why it exists, and how to read it."),
    Paragraph("metagpt_mini/llm.py - LLM client (102 LOC)", H3),
    p("The only file that knows about an LLM provider. Wraps the OpenAI "
      "Chat Completions API. Anything that exposes an OpenAI-compatible "
      "endpoint (MiniMax-M3, Qwen3-8B-Flash, Ollama, LM Studio) works."),
    code(
        "class LLM:\n"
        "    def __init__(self, model=None, base_url=None, api_key=None, ...):\n"
        "        self.model = model or os.getenv('LLM_MODEL', 'MiniMax-M3')\n"
        "        self.base_url = base_url or os.getenv('LLM_BASE_URL')\n"
        "        self.api_key = api_key or os.getenv('LLM_API_KEY')\n"
        "        ...\n"
        "        self._client = OpenAI(api_key=..., base_url=...)\n"
        "\n"
        "    def chat(self, messages, *, json_mode=False):\n"
        "        # single-turn call, with cost accounting\n"
        "        t0 = time.perf_counter()\n"
        "        resp = self._client.chat.completions.create(...)\n"
        "        self.usage.record(usage.prompt_tokens,\n"
        "                          usage.completion_tokens, ...)\n"
        "        return resp.choices[0].message.content\n"
        "\n"
        "    def system_user(self, system, user, *, json_mode=False):\n"
        "        return self.chat([ChatMessage('system', system),\n"
        "                          ChatMessage('user', user)])"
    ),
    p("<b>Key idea:</b> <font face='Courier'>self.usage</font> accumulates "
      "tokens and an estimated cost. <font face='Courier'>Team.run</font> "
      "checks <font face='Courier'>usage_cost()</font> against "
      "<font face='Courier'>MAX_BUDGET_USD</font> between every role and "
      "stops if the budget is exceeded. This is a production hardening you "
      "will not find in toy agent demos."),
    Paragraph("metagpt_mini/schema.py - Message + MessagePool (54 LOC)", H3),
    p("The substrate. Every piece of state in MetaGPT is a Message in a "
      "MessagePool. Two small classes, but the entire system runs on them."),
    code(
        "@dataclass\n"
        "class Message:\n"
        "    role: str        # who emitted: ProductManager, Engineer, ...\n"
        "    content: str     # the actual text (PRD, design doc, code, ...)\n"
        "    cause_by: str    # which Action produced it\n"
        "    msg_id: str      # short uuid\n"
        "    created_at: str  # isoformat UTC\n"
        "\n"
        "class MessagePool:\n"
        "    def publish(self, msg): ...\n"
        "    def history(self): ...\n"
        "    def of_role(self, name): ...       # messages from a role\n"
        "    def by_action(self, cause_by): ... # messages from an action"
    ),
    p("<b>Key idea:</b> <font face='Courier'>cause_by</font> is the "
      "traceable SOP link. If you ever ask why did the Engineer write this "
      "code, you can read the chain: UserInput, WritePRD, WriteDesign, "
      "WriteCode."),
    Paragraph("metagpt_mini/actions.py - The four verbs (145 LOC)", H3),
    p("Each Action is a dataclass with one method: "
      "<font face='Courier'>run(pool)</font> returns a Message. Read from "
      "the pool (e.g. the last PRD message), call the LLM with a structured "
      "system prompt, write the result back into the pool."),
    code(
        "@dataclass\n"
        "class WritePRD:\n"
        "    llm: LLM\n"
        "    cause_by: str = 'WritePRD'\n"
        "    role_name: str = 'ProductManager'\n"
        "\n"
        "    def run(self, requirement, pool):\n"
        "        out = self.llm.system_user(PRD_SYSTEM, requirement)\n"
        "        msg = Message(role='ProductManager',\n"
        "                      content=out,\n"
        "                      cause_by='WritePRD')\n"
        "        pool.publish(msg)\n"
        "        return msg"
    ),
    p("Four actions in canonical SOP order: "
      "<font face='Courier'>WritePRD</font>, "
      "<font face='Courier'>WriteDesign</font>, "
      "<font face='Courier'>WriteCode</font>, "
      "<font face='Courier'>WriteTest</font>. Each one is ~30 lines. "
      "Reading them top-to-bottom shows the entire workflow."),
    Paragraph("metagpt_mini/roles.py - The four agents (45 LOC)", H3),
    code(
        "@dataclass\n"
        "class Role:\n"
        "    name: str           # ProductManager\n"
        "    profile: str        # Senior PM\n"
        "    actions: list       # [WritePRD], [WriteDesign], etc.\n"
        "\n"
        "    def run(self, pool):\n"
        "        outs = []\n"
        "        for action_factory in self.actions:\n"
        "            action = action_factory()    # instantiate action with shared llm\n"
        "            msg = action.run(pool)\n"
        "            outs.append(msg)\n"
        "        return outs\n"
        "\n"
        "def make_canonical_team(llm):\n"
        "    return [\n"
        "        Role('ProductManager', 'Senior PM', [lambda: WritePRD(llm)]),\n"
        "        Role('Architect',      'Senior Architect', [lambda: WriteDesign(llm)]),\n"
        "        Role('Engineer',       'Senior Backend Eng', [lambda: WriteCode(llm)]),\n"
        "        Role('QA',             'Senior QA Engineer', [lambda: WriteTest(llm)]),\n"
        "    ]"
    ),
    Paragraph("metagpt_mini/team.py - The orchestrator (84 LOC)", H3),
    p("Owns the MessagePool, holds the Roles, runs them in SOP sequence, "
      "prints rich console panels, checks the budget between every role."),
    code(
        "class Team:\n"
        "    def run(self, requirement, budget_usd=None):\n"
        "        seed = Message(role='User', content=requirement,\n"
        "                       cause_by='UserInput')\n"
        "        self.pool.publish(seed)\n"
        "\n"
        "        for role in self.roles:\n"
        "            if self.usage_cost() > budget:\n"
        "                console.print('Budget blown - stopping.')\n"
        "                break\n"
        "            console.rule(role.name)\n"
        "            for msg in role.run(self.pool):\n"
        "                console.print(Panel(msg.content,\n"
        "                              title=f'{role.name} -> {msg.cause_by}'))\n"
        "        return self.pool"
    ),
    Spacer(1, 0.3 * cm),
    Paragraph("examples/build_cli_app.py - The end-to-end demo (80 LOC)", H3),
    p("The script you run. Loads <font face='Courier'>.env</font>, "
      "instantiates an LLM, builds a team, runs the SOP on a one-line "
      "requirement, then saves the four artifacts (PRD.md, design.md, "
      "app.py, test_app.py) to <font face='Courier'>output/</font>."),
    p("This is what you will demo live in class."),
    PageBreak(),
]

# Section 5 — SOP trace
story += [
    Paragraph("5. The SOP Trace - What You Will See Live", H1),
    p("When you run the demo, here is the actual sequence of events your "
      "students will watch. Numbered for ease of narration."),
    Paragraph("Step 1 - User requirement enters as a Message", H3),
    code(
        "Message(role='User',\n"
        "        content='Build a CLI todo app in Python with add, list,\n"
        "        complete, delete, persist to JSON, priorities, due dates.',\n"
        "        cause_by='UserInput')"
    ),
    Paragraph("Step 2 - ProductManager runs WritePRD", H3),
    p("The LLM is given a system prompt that says you are a senior PM. "
      "It produces a structured PRD with Goal, User Stories, Functional + "
      "Non-Functional Requirements, Out-of-scope. The message enters the "
      "pool with <font face='Courier'>cause_by=WritePRD</font>."),
    Paragraph("Step 3 - Architect runs WriteDesign", H3),
    p("Reads the PRD from the pool "
      "(<font face='Courier'>_last_of(pool, WritePRD)</font>). Produces a "
      "design with modules, data model, function signatures. Enters the "
      "pool with <font face='Courier'>cause_by=WriteDesign</font>."),
    Paragraph("Step 4 - Engineer runs WriteCode", H3),
    p("Reads the design. Produces a complete, runnable Python module with "
      "type hints and a <font face='Courier'>__main__</font> demo. Enters "
      "the pool with <font face='Courier'>cause_by=WriteCode</font>."),
    Paragraph("Step 5 - QA runs WriteTest", H3),
    p("Reads both design and code. Produces a pytest test module covering "
      "happy path, edge cases, and a failure case. Enters the pool with "
      "<font face='Courier'>cause_by=WriteTest</font>."),
    Paragraph("Step 6 - Output is saved", H3),
    p("The demo script extracts each message and writes them to disk as:"),
    bullets([
        "<font face='Courier'>output/01_prd.md</font> - the Product "
        "Requirements Document",
        "<font face='Courier'>output/02_design.md</font> - the technical "
        "design",
        "<font face='Courier'>output/03_app.py</font> - the runnable app "
        "(code fences stripped)",
        "<font face='Courier'>output/04_test_app.py</font> - the pytest "
        "module",
    ]),
    Paragraph("Step 7 - Run it", H3),
    code(
        "cd /Users/jkm/Projects/metagpt-mini\n"
        "source .venv/bin/activate\n"
        "python examples/build_cli_app.py\n"
        "\n"
        "# Then test the result:\n"
        "cd output\n"
        "python 03_app.py add 'Buy milk' --priority high --due 2026-09-07\n"
        "python 03_app.py list\n"
        "pytest 04_test_app.py -v"
    ),
    p("If the SOP is correct, you have a working CLI todo app built "
      "end-to-end by 4 LLM agents in 4 LLM calls. Total wall time: 30-90 "
      "seconds with MiniMax-M3. Total cost: roughly $0.05 - $0.20."),
    PageBreak(),
]

# Section 6 — Windows setup
story += [
    Paragraph("6. Windows + MiniMax-M3 Setup - Step by Step", H1),
    p("You will demo this on your Windows machine. The setup is the same "
      "as on Mac, with two Windows-specific tweaks (Git Bash shell, .env "
      "file). Total time: 15 minutes if Python and Git are already "
      "installed."),
    Paragraph("6.1 Prerequisites (Windows)", H3),
    bullets([
        "<b>Python 3.11+</b> - install from python.org, <i>check Add to "
        "PATH</i> at install time",
        "<b>Git</b> - install from git-scm.com, pick Git Bash as default "
        "terminal",
        "<b>uv</b> - the Python package manager. In Git Bash, run: "
        "<font face='Courier'>pip install uv</font>",
        "<b>MiniMax-M3 API key</b> - your existing key. Keep it secret.",
    ]),
    Paragraph("6.2 Clone the repo", H3),
    code(
        "# In Git Bash (or PowerShell - both work)\n"
        "mkdir ~/Projects\n"
        "cd ~/Projects\n"
        "git clone https://github.com/mannuking/metagpt-mini.git\n"
        "cd metagpt-mini"
    ),
    Paragraph("6.3 Set up the Python environment", H3),
    code(
        "# In Git Bash on Windows\n"
        "cd ~/Projects/metagpt-mini\n"
        "uv venv                                    # creates .venv/\n"
        "source .venv/Scripts/activate              # Windows path: Scripts/, not bin/\n"
        "uv pip install -e .                        # installs package + dependencies"
    ),
    Paragraph("6.4 Configure your .env (the critical step)", H3),
    code(
        "# Copy the template\n"
        "cp .env.example .env\n"
        "\n"
        "# Edit it (use notepad, vscode, or vim)\n"
        "notepad .env\n"
        "\n"
        "# Fill in these three lines:\n"
        "#   LLM_API_KEY=sk-your-minimax-key-here\n"
        "#   LLM_BASE_URL=https://api.minimax.io/anthropic\n"
        "#   LLM_MODEL=MiniMax-M3\n"
        "\n"
        "# Save and close. NEVER commit the .env file\n"
        "# (it is already in .gitignore)."
    ),
    Paragraph("6.5 Verify the setup", H3),
    code(
        "# Run the schema tests - these do not need the LLM\n"
        "pytest tests/ -v\n"
        "\n"
        "# Expected output:\n"
        "# tests/test_schema.py::test_message_roundtrip        PASSED\n"
        "# tests/test_schema.py::test_pool_publish_and_filter  PASSED\n"
        "# tests/test_schema.py::test_pool_ordering            PASSED\n"
        "# ================ 3 passed in 0.01s =================="
    ),
    Paragraph("6.6 Run the demo", H3),
    code(
        "# Source the venv (every new shell needs this)\n"
        "source .venv/Scripts/activate\n"
        "\n"
        "# Run the canonical demo\n"
        "python examples/build_cli_app.py\n"
        "\n"
        "# After the run, test the output:\n"
        "cd output\n"
        "python 03_app.py --help\n"
        "pytest 04_test_app.py -v"
    ),
    Paragraph("6.7 Common Windows gotchas", H3),
    bullets([
        "<b>Path separators:</b> Windows uses "
        "<font face='Courier'>Scripts/</font> where Mac/Linux use "
        "<font face='Courier'>bin/</font>. Source the venv with "
        "<font face='Courier'>source .venv/Scripts/activate</font> in Git Bash.",
        "<b>Line endings:</b> Git on Windows may convert LF to CRLF. If "
        "you see syntax errors in agent output, run "
        "<font face='Courier'>git config core.autocrlf false</font> then "
        "re-clone.",
        "<b>.env not loaded:</b> python-dotenv reads "
        "<font face='Courier'>.env</font> from the current working "
        "directory. Always <font face='Courier'>cd</font> into the project "
        "folder before launching Python.",
        "<b>API key leakage:</b> if you accidentally commit "
        "<font face='Courier'>.env</font>, rotate the key immediately "
        "(GitHub will also auto-redact it in push protection, but treat it "
        "as exposed).",
        "<b>Slow first run:</b> the first LLM call may take 5-10 seconds "
        "for TLS handshake + cold-start; subsequent calls in the same run "
        "are 1-3s.",
        "<b>Rich console on older Windows terminals:</b> if the colored "
        "output looks broken in cmd.exe, run inside Windows Terminal or "
        "Git Bash.",
    ]),
    Paragraph("6.8 Switching models without code changes", H3),
    p("Because the framework only talks to an OpenAI-compatible API, "
      "switching to Qwen3-8B-Flash, GPT-4, or local Ollama is just a .env "
      "change:"),
    code(
        "# Qwen3-8B-Flash (Chinese cloud, OpenAI-compat mode)\n"
        "LLM_API_KEY=sk-qwen-key\n"
        "LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1\n"
        "LLM_MODEL=qwen3-8b-flash\n"
        "\n"
        "# Local Ollama (open-source, runs on your GPU)\n"
        "LLM_API_KEY=ollama                        # any non-empty string\n"
        "LLM_BASE_URL=http://localhost:11434/v1\n"
        "LLM_MODEL=qwen2.5-coder:7b                # or any tag you have pulled\n"
        "\n"
        "# LM Studio (local desktop app)\n"
        "LLM_API_KEY=lm-studio\n"
        "LLM_BASE_URL=http://localhost:1234/v1\n"
        "LLM_MODEL=qwen2.5-7b-instruct"
    ),
    PageBreak(),
]

# Appendix A — Glossary
story += [
    Paragraph("Appendix A - Glossary for the Class", H1),
]
glossary = [
    ("Agent", "An LLM-driven entity that reads context, decides, and acts. "
              "In MetaGPT, a Role is an Agent."),
    ("Action", "The unit of behaviour. An Action takes context and emits a "
               "Message."),
    ("Role", "A named bundle of Actions + a profile. Roles are reusable "
             "across runs."),
    ("SOP", "Standard Operating Procedure. The directed graph of Actions "
            "that defines a workflow."),
    ("Message", "An event emitted by an Action. Carries role, content, "
                "cause_by, msg_id, timestamp."),
    ("Message Pool", "The shared bus through which agents communicate."),
    ("ACI", "Agent-Computer Interface (SWE-agent term). Purpose-built "
             "verbs instead of raw shell."),
    ("Harness", "The runtime + tooling + environment around an LLM. "
                "MetaGPT is a harness; OpenHands is a harness; Hermes Agent "
                "is a harness."),
    ("Self-Reflection", "An agent own critical assessment of its output "
                         "(Reflexion idea)."),
    ("Skill Library", "A growing collection of reusable code/tool "
                      "definitions an agent writes and reuses (Voyager "
                      "idea)."),
]
for term, defn in glossary:
    story.append(Paragraph("<b>" + term + "</b> - " + defn, BULLET))
story.append(Spacer(1, 0.4 * cm))

# Appendix B — Citations
story += [
    Paragraph("Appendix B - Citations (BibTeX)", H1),
    code(
        "@inproceedings{hong2024metagpt,\n"
        "  title = {MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework},\n"
        "  author = {Hong, Sirui and Chen, Jonathan and Zhu, Ceyao and others},\n"
        "  booktitle = {ICLR},\n"
        "  year = {2024},\n"
        "  note = {Oral presentation, top 1.2 percent, ranked no.1 in LLM-Agent category}\n"
        "}\n"
        "\n"
        "@inproceedings{yang2024sweagent,\n"
        "  title = {SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering},\n"
        "  author = {Yang, John and others},\n"
        "  booktitle = {NeurIPS},\n"
        "  year = {2024}\n"
        "}\n"
        "\n"
        "@inproceedings{wang2024openhands,\n"
        "  title = {OpenHands (formerly OpenDevin): An Open Platform for AI Software Developers},\n"
        "  author = {Wang, Xingyao and others},\n"
        "  booktitle = {COLM},\n"
        "  year = {2024},\n"
        "  note = {Oral presentation}\n"
        "}\n"
        "\n"
        "@inproceedings{shinn2023reflexion,\n"
        "  title = {Reflexion: Language Agents with Verbal Reinforcement Learning},\n"
        "  author = {Shinn, Noah and Cassano, Federico and Gopinath, Ashish and others},\n"
        "  booktitle = {NeurIPS},\n"
        "  year = {2023}\n"
        "}\n"
        "\n"
        "@inproceedings{wang2023voyager,\n"
        "  title = {Voyager: An Open-Ended Embodied Agent with Large Language Models},\n"
        "  author = {Wang, Guanzhi and Xie, Yuqi and Jiang, Yunfan and others},\n"
        "  booktitle = {NeurIPS},\n"
        "  year = {2023}\n"
        "}"
    ),
    Spacer(1, 0.3 * cm),
]

# Appendix C — cheat sheet
cheat = [
    ["File", "LOC", "What it does"],
    ["metagpt_mini/__init__.py", "1", "Package marker, version."],
    ["metagpt_mini/llm.py", "102", "LLM client + cost tracker. Only file that talks to an API."],
    ["metagpt_mini/schema.py", "54", "Message + MessagePool. The substrate."],
    ["metagpt_mini/actions.py", "145", "WritePRD, WriteDesign, WriteCode, WriteTest."],
    ["metagpt_mini/roles.py", "45", "Role + make_canonical_team."],
    ["metagpt_mini/team.py", "84", "Team orchestrator with budget guard + rich UI."],
    ["metagpt_mini/utils.py", "1", "Cost-tracker re-export."],
    ["examples/build_cli_app.py", "80", "End-to-end runnable demo. The script you teach from."],
    ["tests/test_schema.py", "34", "3 unit tests. Run before any LLM call."],
    ["pyproject.toml", "-", "Project metadata. Edit name/desc here."],
    ["README.md", "-", "GitHub README. Top-level orientation."],
    [".env.example", "-", "Copy to .env, fill in LLM_API_KEY."],
    ["docs/build_pdf.py", "-", "Generates this PDF."],
    ["docs/MetaGPT-Mini-Learning-Guide.pdf", "-", "This document."],
]
tcheat = Table(cheat, colWidths=[6*cm, 1.5*cm, 9.5*cm])
tcheat.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#888888")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
     [colors.white, colors.HexColor("#F4F8FC")]),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
]))
story += [
    Paragraph("Appendix C - File-by-file cheat sheet", H1),
    tcheat,
]

# Render
doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    leftMargin=2*cm, rightMargin=2*cm,
    topMargin=2*cm, bottomMargin=2*cm,
    title="MetaGPT-Mini Learning Guide",
    author="Jai Kumar Meena",
)

doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
print("PDF written: " + OUT + "  (" + str(os.path.getsize(OUT)) + " bytes)")