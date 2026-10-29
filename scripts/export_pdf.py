"""render every saved notebook cell, code block and output into a readable pdf."""
from pathlib import Path
import base64,io,json,re,textwrap
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,Preformatted,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
ROOT=Path(__file__).resolve().parents[1]
FONT=Path('/System/Library/Fonts/Supplemental')
if not FONT.exists():
    import reportlab
    FONT=Path(reportlab.__file__).parent/'fonts'
for name,file in [('Body','Arial.ttf'),('BodyBold','Arial Bold.ttf'),('Mono','Courier New.ttf')]:
    fallback={'Body':'Vera.ttf','BodyBold':'VeraBd.ttf','Mono':'Vera.ttf'}
    pdfmetrics.registerFont(TTFont(name,str(FONT/file if (FONT/file).exists() else FONT/fallback[name])))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='BodyBold',italic='Body',boldItalic='BodyBold')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle('Text',fontName='Body',fontSize=9.5,leading=14,spaceAfter=8))
styles.add(ParagraphStyle('CodeBlock',fontName='Mono',fontSize=7,leading=9,spaceAfter=8,
                          backColor=colors.HexColor('#f3f6f8'),borderPadding=6))
for name,size in [('Title',22),('Heading1',17),('Heading2',13),('Heading3',11)]:
    styles[name].fontName='BodyBold';styles[name].fontSize=size;styles[name].leading=size*1.25;styles[name].keepWithNext=True
story=[]

def inline(text):
    text=text.replace('\u2011','-').replace('\u2013','-').replace('\u2014','-')
    text=escape(text)
    text=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
    text=re.sub(r'`([^`]+)`',r'<font name="Mono">\1</font>',text)
    text=re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',r'<link href="\2" color="#126c89">\1</link>',text)
    return text

def markdown(source):
    for paragraph in source.split('\n\n'):
        paragraph=paragraph.strip()
        if not paragraph:continue
        if paragraph.startswith('#'):
            for line in paragraph.splitlines():
                if line.startswith('#'):
                    level=len(line)-len(line.lstrip('#'))
                    name={1:'Title',2:'Heading1',3:'Heading2'}.get(level,'Heading3')
                    story.append(Paragraph(inline(line.lstrip('#').strip()),styles[name]))
                else:story.append(Paragraph(inline(line),styles['Text']))
        else:
            for line in paragraph.splitlines() if paragraph.startswith('- ') else [paragraph]:
                story.append(Paragraph(inline(line.replace('\n','<br/>')).replace('&lt;br/&gt;','<br/>'),styles['Text']))

def preformatted(source):
    source=re.sub(r'\x1b\[[0-9;]*m','',source)
    lines=[]
    for line in source.splitlines():
        lines.extend(textwrap.wrap(line,width=103,replace_whitespace=False,drop_whitespace=False,break_long_words=True,break_on_hyphens=False) or [''])
    #split text into short flowables so long code and table outputs can paginate
    for i in range(0,len(lines),35):story.append(Preformatted('\n'.join(lines[i:i+35]),styles['CodeBlock']))

notebook=json.loads((ROOT/'notebooks/IND320_Project(P3).ipynb').read_text())
for cell in notebook['cells']:
    source=''.join(cell.get('source',[]))
    if cell['cell_type']=='markdown':markdown(source)
    else:
        story.append(Paragraph(f"Code cell [{cell.get('execution_count', '')}]",styles['Heading3']))
        preformatted(source)
        for output in cell.get('outputs',[]):
            if output.get('output_type')=='error':raise RuntimeError('Do not export a notebook with execution errors.')
            data=output.get('data',{})
            if 'image/png' in data:
                encoded=data['image/png'];encoded=''.join(encoded) if isinstance(encoded,list) else encoded
                image=Image(io.BytesIO(base64.b64decode(encoded)))
                factor=min(480/image.imageWidth,400/image.imageHeight)
                image.drawWidth=image.imageWidth*factor;image.drawHeight=image.imageHeight*factor
                story.append(image);story.append(Spacer(1,10))
            elif 'text/markdown' in data:markdown(''.join(data['text/markdown']))
            elif 'text/plain' in data:preformatted(''.join(data['text/plain']))
            elif 'text' in output:preformatted(''.join(output['text']))
        story.append(Spacer(1,10))

def page(canvas,doc):
    canvas.saveState();canvas.setFont('Body',8);canvas.setFillColor(colors.HexColor('#61737d'))
    canvas.drawString(42,24,'IND320 | Part 3 | executed notebook')
    canvas.drawRightString(A4[0]-42,24,str(doc.page));canvas.restoreState()
path=ROOT/'reports/IND320_Project(P3).pdf'
doc=SimpleDocTemplate(str(path),pagesize=A4,leftMargin=42,rightMargin=42,topMargin=40,bottomMargin=42,
                      title='IND320 Project Part 3',author='IND320 project')
doc.build(story,onFirstPage=page,onLaterPages=page)
print(path)
