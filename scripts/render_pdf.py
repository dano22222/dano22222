"""render the report for visual quality control without changing the pdf"""
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'reports/pdf_preview';folder.mkdir(exist_ok=True)
document=pdfium.PdfDocument(ROOT/'reports/IND320_Project(P3).pdf')
thumbnails=[]
for index in range(len(document)):
    page=document[index].render(scale=1.5).to_pil()
    page.save(folder/f'page_{index+1:02}.png')
    page.thumbnail((300,430));thumbnails.append(page.copy())
for start in range(0,len(thumbnails),12):
    sheet=Image.new('RGB',(1200,1440),'#cdd4d8');draw=ImageDraw.Draw(sheet)
    for index,thumbnail in enumerate(thumbnails[start:start+12]):
        x=(index%4)*300;y=(index//4)*480
        sheet.paste(thumbnail,(x,y+25));draw.text((x+12,y+5),str(start+index+1),fill='black')
    sheet.save(folder/f'contact_{start//12+1}.png')
print(f'rendered {len(document)} pages to {folder}')
