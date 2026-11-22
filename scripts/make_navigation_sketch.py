"""draws the navigation sketch of the streamlit app (notebooks/figures/navigation_sketch.png)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
groups=[('START','#1F6F8B',['Overview (front page)','Map and selection']),
        ('EXPLORE','#3D9970',['Data overview\n(NVE table, sparklines,\nexchange rates)','Reservoir plots','Electricity flows\n(MongoDB)']),
        ('ANOMALIES','#E07A5F',['Weather SATV and LOF','STL and spectrogram']),
        ('PREDICT','#6C5B7B',['Weather correlation','Forecast filling'])]
fig,ax=plt.subplots(figsize=(13,7.2)); ax.set_xlim(0,13); ax.set_ylim(0,7.2); ax.axis('off')
ax.text(.2,6.85,'IND320 app: navigation sketch (Part 4)',fontsize=16,weight='bold',color='#1B2A34')
ax.text(.2,6.5,'Sidebar groups follow the type of task. Each page shows a band in its group colour.',fontsize=10,color='#555')
pos={}
for i,(name,color,pages) in enumerate(groups):
    x=.3+i*3.15
    ax.add_patch(FancyBboxPatch((x,1.55),2.85,4.6,boxstyle='round,pad=0.02,rounding_size=0.12',fc=color+'18',ec=color,lw=2))
    ax.text(x+1.42,5.85,name,ha='center',fontsize=13,weight='bold',color=color)
    for j,p in enumerate(pages):
        y=5.0-j*1.2
        ax.add_patch(FancyBboxPatch((x+.2,y-.42),2.45,.84,boxstyle='round,pad=0.02,rounding_size=0.08',fc='white',ec=color,lw=1.2))
        ax.text(x+1.42,y,p,ha='center',va='center',fontsize=9.2,color='#1B2A34')
        pos[p.split('\n')[0]]=(x+1.42,y)
#global state box
ax.add_patch(FancyBboxPatch((.3,.15),12.6,1.1,boxstyle='round,pad=0.02,rounding_size=0.1',fc='#F3F7F9',ec='#8A9BA8',lw=1.2,ls='--'))
ax.text(.5,.95,'st.session_state (global selections)',fontsize=10.5,weight='bold',color='#1B2A34')
ax.text(.5,.45,'reservoir_selection: area (sidebar or map click)   |   time_frame: weeks chosen on the map'
        '   |   weather_property (default temperature)',fontsize=9.5,color='#1B2A34')
#the map writes the global selections; the other groups read them
def arrow(x0,y0,x1,y1,color):
    ax.add_patch(FancyArrowPatch((x0,y0),(x1,y1),arrowstyle='-|>',mutation_scale=14,color=color,lw=1.6))
mx=pos['Map and selection'][0]
arrow(mx,3.38,mx,1.27,'#1F6F8B'); ax.text(mx+.08,2.2,'writes\n(click, time\nframe)',fontsize=8.5,color='#1F6F8B')
for i,color in [(1,'#3D9970'),(2,'#E07A5F'),(3,'#6C5B7B')]:
    x=.3+i*3.15+1.42
    arrow(x,1.27,x,1.53,color)
ax.text(12.7,.95,'all groups read the selections',fontsize=8.5,color='#6b7c88',ha='right',style='italic')
fig.savefig('notebooks/figures/navigation_sketch.png',dpi=130,bbox_inches='tight',facecolor='white')
