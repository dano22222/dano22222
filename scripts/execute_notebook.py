"""execute the saved part 3 notebook and export all code, outputs and figures."""
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'notebooks/IND320_Project(P3).ipynb'
notebook=nbformat.read(path,as_version=4)
client=NotebookClient(notebook,timeout=240,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}})
client.execute()
nbformat.write(notebook,path)
body,_=HTMLExporter().from_notebook_node(notebook)
(ROOT/'reports/IND320_Project(P3).html').write_text(body)
print('Executed cells:',sum(c.cell_type=='code' for c in notebook.cells))
print('HTML export:',ROOT/'reports/IND320_Project(P3).html')
