from PIL import Image, ImageDraw, ImageFont
import math, os, subprocess, wave, struct

ROOT=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(ROOT,'Decision_Room_First_Five_Minutes.mp4')
W=H=1080
NAVY=(7,16,31); TEAL=(48,226,207); WHITE=(242,247,251); MUTED=(166,183,200); RED=(255,75,91); GOLD=(249,190,89)
font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
bold_path='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def font(size,bold=False): return ImageFont.truetype(bold_path if bold else font_path,size)
scenes=[
 ('THE PHONE RINGS.','Nobody answers.','A serious incident is unfolding.', '01 / THE SIGNAL', TEAL),
 ('PRIVILEGED ACCESS','A powerful account is behaving strangely.','The facts are incomplete. The clock is not.', '02 / THE THREAT', RED),
 ('TWO TEAMS. TWO ANSWERS.','Group says wait. The subsidiary says act.','Both see a real risk. Who decides?', '03 / THE CONFLICT', GOLD),
 ('THE CISO IS UNREACHABLE.','The usual decision-maker is offline.','The response plan is open on the desk.', '04 / THE GAP', RED),
 ('FIVE MINUTES.','Who has authority? What can happen now?','When do we escalate, and who owns the remaining risk?', '05 / THE TEST', TEAL),
 ('READY BEFORE THE CRISIS.','A plan is useful. A decision path must work.','Stress-test authority under pressure.', 'PALM92  /  CYBER RESILIENCE', TEAL),
]
def draw_scene(i, scene):
    label,title,sub,eyebrow,accent=scene
    im=Image.new('RGB',(W,H),NAVY)
    px=im.load()
    for y in range(H):
        for x in range(W):
            glow=max(0,1-math.sqrt(((x-760)/850)**2+((y-360)/700)**2))
            px[x,y]=(int(NAVY[0]+4*glow),int(NAVY[1]+28*glow),int(NAVY[2]+42*glow))
    d=ImageDraw.Draw(im,'RGBA')
    for x in range(0,W,72): d.line((x,0,x,H),fill=(120,160,190,18),width=1)
    for y in range(0,H,72): d.line((0,y,W,y),fill=(120,160,190,18),width=1)
    d.rounded_rectangle((58,55,1022,1025),radius=34,outline=(120,170,200,38),width=2)
    d.rounded_rectangle((96,100,984,110),radius=5,fill=(40,68,91,180))
    d.rounded_rectangle((96,100,96+int(888*(i+1)/6),110),radius=5,fill=accent)
    d.text((96,150),eyebrow,font=font(23,True),fill=accent)
    # Five minute timer treatment
    cx,cy=850,270
    d.ellipse((cx-78,cy-78,cx+78,cy+78),outline=(accent[0],accent[1],accent[2],65),width=3)
    d.arc((cx-78,cy-78,cx+78,cy+78),-90,-90+(i+1)*55,fill=accent,width=8)
    d.text((cx,cy),f'0{i}:00',font=font(29,True),fill=WHITE,anchor='mm')
    d.text((96,325),label,font=font(39,True),fill=MUTED)
    words=title.split(); lines=[]; current=''
    for word in words:
        test=(current+' '+word).strip()
        if d.textbbox((0,0),test,font=font(64,True))[2] > 820 and current:
            lines.append(current); current=word
        else: current=test
    if current: lines.append(current)
    y=425
    for line in lines:
        d.text((96,y),line,font=font(64,True),fill=WHITE,stroke_width=0)
        y+=82
    # Accent marker
    d.rounded_rectangle((96,y+15,178,y+23),radius=4,fill=accent)
    # Subtitle wraps to clean lines
    words=sub.split(); lines=[]; current=''
    for word in words:
        test=(current+' '+word).strip()
        if d.textbbox((0,0),test,font=font(33))[2] > 830 and current:
            lines.append(current); current=word
        else: current=test
    if current: lines.append(current)
    yy=y+62
    for line in lines:
        d.text((96,yy),line,font=font(33),fill=WHITE); yy+=48
    # Bottom cue / time pressure
    d.text((96,920),'AUTHORITY  •  ESCALATION  •  EVIDENCE',font=font(18,True),fill=(157,183,199))
    im.save(os.path.join(ROOT,'scenes',f'scene_{i+1:02d}.png'))

for i,s in enumerate(scenes): draw_scene(i,s)
# Six 7-second panels, gentle push-in and fades, assembled by FFmpeg.
clips=[]
for i in range(6):
    src=os.path.join(ROOT,'scenes',f'scene_{i+1:02d}.png')
    dst=os.path.join(ROOT,'scenes',f'clip_{i+1:02d}.mp4')
    vf="zoompan=z='min(zoom+0.00018,1.04)':d=175:s=1080x1080:fps=25,fade=t=in:st=0:d=0.25,fade=t=out:st=6.6:d=0.4,format=yuv420p"
    subprocess.run(['ffmpeg','-y','-loglevel','error','-loop','1','-i',src,'-vf',vf,'-t','7','-r','25','-an','-c:v','libx264','-preset','fast','-crf','22',dst],check=True)
    clips.append(dst)
concat=os.path.join(ROOT,'scenes','clips.txt')
with open(concat,'w') as f:
    for p in clips: f.write("file '"+os.path.basename(p)+"'\n")
video=os.path.join(ROOT,'video_only.mp4')
subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',concat,'-c','copy',video],check=True)
# Create a low-volume original suspense bed and subtle pulse. No third-party music.
audio=os.path.join(ROOT,'scenes','pulse.wav'); rate=44100; duration=42
with wave.open(audio,'wb') as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
    for n in range(rate*duration):
        t=n/rate
        env=min(1,t/2)*min(1,(duration-t)/2)
        tone=0.10*math.sin(2*math.pi*55*t)+0.04*math.sin(2*math.pi*(82+2*math.sin(t*0.18))*t)
        beat=0.08*math.exp(-((t%1.5)/0.065)**2)
        val=int(max(-1,min(1,(tone+beat)*env))*32767)
        wf.writeframesraw(struct.pack('<h',val))
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',video,'-i',audio,'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',OUT],check=True)
print(OUT)
