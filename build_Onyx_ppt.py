from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.oxml.xmlchemy import OxmlElement
from pptx.enum.text import MSO_AUTO_SIZE
import os, glob

SRC = glob.glob(r'C:\Users\Ronit Sharma\Downloads\*.pptx')[0]
OUT = r'D:\Onyx\Onyx_SIH2026_Remade.pptx'
prs = Presentation(SRC)
W, H = prs.slide_width, prs.slide_height
NAVY = RGBColor(24, 61, 105); BLUE = RGBColor(37, 116, 210); INK = RGBColor(31, 41, 55)
MUTED = RGBColor(91, 105, 122); PALE = RGBColor(241, 246, 251); GREEN = RGBColor(42, 145, 96)
ORANGE = RGBColor(239, 126, 45); RED = RGBColor(208, 67, 67); WHITE = RGBColor(255,255,255)

def remove_all(slide):
    for sh in list(slide.shapes):
        sp = sh._element
        sp.getparent().remove(sp)

def bg(slide):
    fill=slide.background.fill; fill.solid(); fill.fore_color.rgb=WHITE
    # thin blue header and footer rules
    bar=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,0,W,Inches(.09)); bar.fill.solid(); bar.fill.fore_color.rgb=BLUE; bar.line.fill.background()
    foot=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,H-Inches(.07),W,Inches(.07)); foot.fill.solid(); foot.fill.fore_color.rgb=NAVY; foot.line.fill.background()

def tx(slide, text, x,y,w,h, size=22, color=INK, bold=False, align=PP_ALIGN.LEFT, font='Arial', italic=False):
    box=slide.shapes.add_textbox(x,y,w,h); tf=box.text_frame; tf.clear(); tf.word_wrap=True; tf.margin_left=Inches(.04); tf.margin_right=Inches(.04); tf.margin_top=Inches(.02); tf.vertical_anchor=MSO_ANCHOR.TOP
    p=tf.paragraphs[0]; p.alignment=align; r=p.add_run(); r.text=text; r.font.name=font; r.font.size=Pt(size); r.font.bold=bold; r.font.italic=italic; r.font.color.rgb=color
    return box

def title(slide, text, kicker=None):
    if kicker: tx(slide,kicker.upper(),Inches(.75),Inches(.30),Inches(8),Inches(.28),11,BLUE,True)
    tx(slide,text,Inches(.75),Inches(.58),Inches(17.5),Inches(.65),30,NAVY,True)

def footer(slide, num):
    tx(slide,'ONYX  |  ALGORYTHMS',Inches(.75),H-Inches(.42),Inches(7),Inches(.2),10,MUTED,True)
    tx(slide,str(num),W-Inches(1.2),H-Inches(.46),Inches(.5),Inches(.24),11,NAVY,True,PP_ALIGN.RIGHT)

def pill(slide, text, x,y,w, color=PALE, fg=NAVY):
    s=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,x,y,w,Inches(.34)); s.fill.solid(); s.fill.fore_color.rgb=color; s.line.color.rgb=color
    tx(slide,text,x+Inches(.08),y+Inches(.065),w-Inches(.16),Inches(.2),11,fg,True,PP_ALIGN.CENTER)

def card(slide,x,y,w,h,head,body,accent=BLUE):
    s=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,x,y,w,h); s.fill.solid(); s.fill.fore_color.rgb=PALE; s.line.color.rgb=RGBColor(215,225,236); s.line.width=Pt(1)
    a=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,x,y,Inches(.09),h); a.fill.solid(); a.fill.fore_color.rgb=accent; a.line.fill.background()
    tx(slide,head,x+Inches(.25),y+Inches(.18),w-Inches(.35),Inches(.3),16,NAVY,True)
    tx(slide,body,x+Inches(.25),y+Inches(.62),w-Inches(.4),h-Inches(.72),14,INK,False)

def mind_node(slide, text, x,y,w,h, fill=WHITE, line=BLUE, size=13, bold=False):
    s=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,x,y,w,h); s.fill.solid(); s.fill.fore_color.rgb=fill; s.line.color.rgb=line; s.line.width=Pt(1.4)
    tx(slide,text,x+Inches(.05),y+Inches(.08),w-Inches(.1),h-Inches(.12),size,line,bold,PP_ALIGN.CENTER)
    return s

def connect(slide,x1,y1,x2,y2,color=RGBColor(160,177,196)):
    c=slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,x1,y1,x2,y2); c.line.color.rgb=color; c.line.width=Pt(1.4); c.line.dash_style=MSO_LINE_DASH_STYLE.ROUND_DOT

for i,slide in enumerate(prs.slides,1):
    remove_all(slide); bg(slide)
    if i==1:
        tx(slide,'SMART INDIA HACKATHON 2026',Inches(.75),Inches(.42),Inches(13),Inches(.45),22,NAVY,True)
        tx(slide,'Onyx',Inches(.75),Inches(1.55),Inches(8),Inches(.8),48,BLUE,True)
        tx(slide,'Evidence-driven Windows SOC platform',Inches(.78),Inches(2.35),Inches(10),Inches(.45),24,INK,False)
        tx(slide,'Automated AI Threat Simulation and Proactive Cyber Defense',Inches(.78),Inches(3.10),Inches(10.5),Inches(.7),21,NAVY,True)
        fields='Problem Statement ID – SIH26145\nProblem Statement Title – Automated AI Threat Simulation and Proactive Cyber Defense\nTheme – Cybersecurity & Defense\nPS Category – Software\nTeam ID – [registered team ID]\nTeam Name – ALGORYTHMS'
        tx(slide,fields,Inches(.8),Inches(4.15),Inches(10.8),Inches(2.25),15,INK)
        # right-side product mark
        s=slide.shapes.add_shape(MSO_SHAPE.HEXAGON,Inches(13.5),Inches(1.6),Inches(4.4),Inches(4.4)); s.fill.solid(); s.fill.fore_color.rgb=PALE; s.line.color.rgb=RGBColor(218,228,239)
        tx(slide,'LIVE',Inches(14.2),Inches(2.25),Inches(3),Inches(.5),18,GREEN,True,PP_ALIGN.CENTER)
        tx(slide,'DEFENDER\n→\nEVIDENCE\n→\nACTION',Inches(14.1),Inches(2.95),Inches(3.2),Inches(2.1),23,NAVY,True,PP_ALIGN.CENTER)
        footer(slide,1)
    elif i==2:
        title(slide,'The Onyx idea','01  PRODUCT CONCEPT')
        tx(slide,'Small and mid-size SOC teams need one trusted view of what is live, what is affected, and what action is authorized.',Inches(.78),Inches(1.35),Inches(11.4),Inches(.55),18,INK)
        card(slide,Inches(.8),Inches(2.15),Inches(5.2),Inches(2.1),'Reality mode','Source-attributed endpoint heartbeats, Defender detections, incidents, topology evidence, notifications, and authorized containment.',BLUE)
        card(slide,Inches(6.25),Inches(2.15),Inches(5.2),Inches(2.1),'World model','Offline attack simulation explores thousands of paths without touching production infrastructure. Results remain clearly labeled as simulated.',ORANGE)
        # mindmap
        tx(slide,'PRODUCT MIND MAP',Inches(12.2),Inches(1.35),Inches(4),Inches(.3),12,BLUE,True,PP_ALIGN.CENTER)
        cx,cy=Inches(14.2),Inches(3.55); mind_node(slide,'Onyx',cx-Inches(.7),cy-Inches(.28),Inches(1.4),Inches(.56),NAVY,NAVY,17,True); # white text override
        # center text manually
        for t in slide.shapes[-1].text_frame.paragraphs[0].runs: t.font.color.rgb=WHITE
        nodes=[('Live assets',Inches(12.1),Inches(2.15),BLUE),('Incidents',Inches(15.05),Inches(2.15),RED),('Topology',Inches(12.0),Inches(4.7),GREEN),('Simulation',Inches(15.0),Inches(4.7),ORANGE)]
        for txtv,x,y,col in nodes:
            mind_node(slide,txtv,x,y,Inches(1.7),Inches(.52),WHITE,col,12,True); connect(slide,cx,cy,x+Inches(.85),y+Inches(.26),col)
        footer(slide,2)
    elif i==3:
        title(slide,'Technical approach','02  ARCHITECTURE')
        tx(slide,'A verified data path connects Windows endpoints to operational decisions. Every incident and graph edge keeps its provenance.',Inches(.78),Inches(1.28),Inches(15.8),Inches(.5),18,INK)
        steps=[('1','Windows agent','Heartbeat, Defender health, detections, device identity'),('2','Appliance API','TLS auth, idempotent ingest, event bookmarks'),('3','Evidence graph','Assets, observed links, incidents, freshness'),('4','SOC actions','Notifications, resolve, queue containment')]
        y=Inches(2.15)
        for n,h,b in steps:
            pill(slide,n,Inches(.9),y+Inches(.16),Inches(.42),BLUE,WHITE); card(slide,Inches(1.5),y,Inches(4.0),Inches(1.25),h,b,BLUE); y+=Inches(1.42)
        # architecture mindmap
        tx(slide,'EVIDENCE MIND MAP',Inches(11.9),Inches(1.55),Inches(4.6),Inches(.3),12,BLUE,True,PP_ALIGN.CENTER)
        cx,cy=Inches(14.2),Inches(4.1); mind_node(slide,'Evidence',cx-Inches(.85),cy-Inches(.3),Inches(1.7),Inches(.6),NAVY,NAVY,16,True)
        for t in slide.shapes[-1].text_frame.paragraphs[0].runs: t.font.color.rgb=WHITE
        nodes=[('Identity',Inches(12.0),Inches(2.25),BLUE),('Freshness',Inches(15.05),Inches(2.25),GREEN),('Provenance',Inches(11.9),Inches(5.2),ORANGE),('Audit trail',Inches(15.1),Inches(5.2),RED)]
        for txtv,x,y,col in nodes: mind_node(slide,txtv,x,y,Inches(1.8),Inches(.52),WHITE,col,12,True); connect(slide,cx,cy,x+Inches(.9),y+Inches(.26),col)
        footer(slide,3)
    elif i==4:
        title(slide,'Feasibility and viability','03  DELIVERY')
        card(slide,Inches(.85),Inches(1.45),Inches(5.3),Inches(2.15),'Feasible now','Windows endpoint heartbeat and authenticated telemetry are lightweight enough for an appliance deployment. The simulator runs offline and safely.',GREEN)
        card(slide,Inches(6.45),Inches(1.45),Inches(5.3),Inches(2.15),'Controlled rollout','Start with enrollment and Defender incidents. Add observed topology, vulnerability inventory, then unlock exposure and patch ROI analytics.',BLUE)
        card(slide,Inches(12.05),Inches(1.45),Inches(5.3),Inches(2.15),'Known risks','Corporate execution policy, incomplete coverage, stale agents, and GPU availability. The product surfaces these gaps instead of inventing data.',ORANGE)
        tx(slide,'READINESS GATES',Inches(.85),Inches(4.25),Inches(5),Inches(.3),13,BLUE,True)
        gates=[('Endpoint enrolled','Live heartbeat within 10 seconds',GREEN),('Incident evidence','Defender or safe simulator event',RED),('Analytics unlocked','Observed links + vulnerability findings',BLUE)]
        for j,(h,b,col) in enumerate(gates):
            y=Inches(4.72)+j*Inches(.6); s=slide.shapes.add_shape(MSO_SHAPE.OVAL,Inches(.9),y,Inches(.25),Inches(.25)); s.fill.solid(); s.fill.fore_color.rgb=col; s.line.fill.background(); tx(slide,h,Inches(1.35),y-Inches(.02),Inches(3.2),Inches(.24),14,NAVY,True); tx(slide,b,Inches(4.8),y-Inches(.02),Inches(7.3),Inches(.24),13,INK)
        footer(slide,4)
    elif i==5:
        title(slide,'Impact and benefits','04  OUTCOMES')
        tx(slide,'Onyx gives a small SOC a dependable operating loop: detect, verify, prioritize, contain, and learn.',Inches(.8),Inches(1.25),Inches(15),Inches(.45),18,INK)
        card(slide,Inches(.8),Inches(2.0),Inches(4.0),Inches(2.2),'Faster triage','Affected endpoints turn red automatically. Analysts see the incident summary, evidence source, freshness, and next action in one place.',RED)
        card(slide,Inches(5.0),Inches(2.0),Inches(4.0),Inches(2.2),'Safer decisions','Reality views use only source-attributed data. World-model simulations remain offline and clearly labeled, with saved runs and evidence panels.',BLUE)
        card(slide,Inches(9.2),Inches(2.0),Inches(4.0),Inches(2.2),'Lower effort','Persistent notifications, role-gated containment, and audit history reduce context switching during an incident.',GREEN)
        # workflow strip
        labels=['Detect','Verify','Prioritize','Contain','Resolve']; cols=[RED,ORANGE,BLUE,NAVY,GREEN]
        for j,l in enumerate(labels):
            x=Inches(1.2)+j*Inches(3.15); mind_node(slide,l,x,Inches(5.25),Inches(1.65),Inches(.55),WHITE,cols[j],13,True)
            if j<4: connect(slide,x+Inches(1.65),Inches(5.52),x+Inches(2.95),Inches(5.52),cols[j])
        footer(slide,5)
    else:
        title(slide,'Research and references','05  FOUNDATION')
        tx(slide,'Onyx combines established security telemetry patterns with research-backed graph and world-model methods.',Inches(.78),Inches(1.28),Inches(15.8),Inches(.45),18,INK)
        refs=[('Windows telemetry','Microsoft Defender event logs, stable endpoint identity, authenticated heartbeat and idempotent event ingestion.'),('Graph modeling','NetworkX and graph neural network concepts for assets, observed relationships, freshness, and confidence.'),('World-model simulation','Model-based reinforcement learning concepts for offline attack-path exploration and replay.'),('Operational controls','Role checks, queued containment, persistent notifications, incident audit, and explicit recovery paths.')]
        for j,(h,b) in enumerate(refs):
            x=Inches(.9)+(j%2)*Inches(8.5); y=Inches(2.05)+(j//2)*Inches(2.0); card(slide,x,y,Inches(7.5),Inches(1.55),h,b,[BLUE,ORANGE,GREEN,RED][j])
        tx(slide,'Source deck fields retained on title slide. Reference PDF used for structure and visual hierarchy only.',Inches(.9),Inches(6.35),Inches(15),Inches(.3),11,MUTED,False,italic=True)
        footer(slide,6)

prs.save(OUT)
print(OUT)
