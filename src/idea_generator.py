from __future__ import annotations

import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', 'output'))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
IDEAS_PER_SECTION = max(4, min(int(os.getenv('IDEAS_PER_SECTION', '8')), 8))
OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'openai/gpt-oss-20b:free')
# The old code requested 30,000 tokens and got HTTP 402. Never do that here.
OPENROUTER_MAX_TOKENS = max(250, min(int(os.getenv('OPENROUTER_MAX_TOKENS', '700')), 700))
USE_OPENROUTER = os.getenv('USE_OPENROUTER', 'false').lower() in {'1','true','yes','on'}

SECTIONS = [
    ('india_trends', '1. India YouTube Trends'),
    ('world_trends', '2. World YouTube Trends'),
    ('genre_trends', '3. YouTube Genre Trends'),
    ('trend_shorts', '4. Trend-Based Shorts Ideas'),
    ('trend_longform', '5. Trend-Based Longform Ideas'),
    ('general_shorts', '6. General India + World Shorts Ideas'),
    ('general_longform', '7. General India + World Longform Ideas'),
    ('genre_fusion', '8. Genre-Fusion High-CTR Ideas'),
]

GENRE_WORDS = {
    'Thriller': ['thriller','suspense','mystery','secret','hidden','missing','unknown','dark'],
    'Crime': ['crime','criminal','murder','robbery','police','case','investigation','scam','fraud'],
    'Comedy': ['comedy','funny','prank','reaction','fun'],
    'Horror': ['horror','ghost','haunted','scary','demon','fear'],
    'Romance': ['love','romance','couple','relationship','wedding'],
    'Action': ['action','fight','war','battle','chase'],
    'Gaming': ['minecraft','gta','gaming','gameplay','fortnite','roblox','game'],
    'Technology': ['ai','technology','tech','phone','iphone','android','app','robot'],
    'Challenge': ['challenge','24 hours','experiment','testing','tried'],
}


def clean(v: Any) -> str:
    if v is None: return ''
    if isinstance(v, str): return re.sub(r'\s+', ' ', v).strip()
    return str(v).strip()


def num(v: Any, default=0) -> int:
    try: return int(float(v))
    except (TypeError, ValueError): return default


def video_title(x: Any) -> str:
    if isinstance(x, str): return clean(x)
    if not isinstance(x, dict): return ''
    for k in ('title','video_title','name','videoTitle','snippet_title'):
        if clean(x.get(k)): return clean(x[k])
    return ''


def video_url(x: Any) -> str:
    if not isinstance(x, dict): return ''
    for k in ('url','video_url','watch_url','link','webpage_url'):
        u = clean(x.get(k))
        if u.startswith(('http://','https://')): return u
    vid = x.get('videoId') or x.get('video_id') or x.get('id')
    return f'https://www.youtube.com/watch?v={vid}' if vid else ''


def extract_videos(data: Any, limit=80) -> list[dict[str, str]]:
    out, seen = [], set()
    def walk(x):
        if len(out) >= limit: return
        if isinstance(x, dict):
            t = video_title(x)
            if t and t.lower() not in seen:
                seen.add(t.lower())
                out.append({'title': t[:220], 'url': video_url(x)})
            for v in x.values():
                if isinstance(v, (dict,list,tuple)): walk(v)
        elif isinstance(x, (list,tuple)):
            for v in x:
                walk(v)
                if len(out) >= limit: return
    walk(data)
    return out


def extract_trends(data: Any, limit=50) -> list[dict[str, Any]]:
    out, seen = [], set()
    def walk(x):
        if len(out) >= limit: return
        if isinstance(x, dict):
            t = clean(x.get('trend') or x.get('topic') or x.get('keyword') or x.get('query'))
            signal = any(k in x for k in ('mentions','combined_views','avg_views','total_views','count','subgenre','category'))
            if t and signal:
                key = (t.lower(), clean(x.get('subgenre') or x.get('genre')).lower())
                if key not in seen:
                    seen.add(key)
                    out.append({
                        'trend': t[:180],
                        'mentions': num(x.get('mentions') or x.get('count')),
                        'combined_views': num(x.get('combined_views') or x.get('total_views') or x.get('views')),
                        'avg_views': num(x.get('avg_views') or x.get('average_views')),
                        'category': clean(x.get('category') or x.get('category_name')),
                        'subgenre': clean(x.get('subgenre') or x.get('genre') or x.get('subcategory')),
                    })
            for v in x.values():
                if isinstance(v,(dict,list,tuple)): walk(v)
        elif isinstance(x,(list,tuple)):
            for v in x:
                walk(v)
                if len(out) >= limit: return
    walk(data)
    out.sort(key=lambda z:(z['combined_views'],z['mentions'],z['avg_views']), reverse=True)
    return out


def infer_genre(trend: dict[str, Any]) -> str:
    explicit = clean(trend.get('subgenre') or trend.get('genre'))
    if explicit and explicit.lower() not in {'entertainment','movies & entertainment','general','other'}:
        return explicit
    text = f"{trend.get('trend','')} {trend.get('category','')}".lower()
    scores = Counter()
    for genre, words in GENRE_WORDS.items():
        for word in words:
            if word in text: scores[genre] += 1
    return scores.most_common(1)[0][0] if scores else 'Entertainment'


def stats(t: dict[str, Any]) -> str:
    p=[]
    if t.get('mentions'): p.append(f"{t['mentions']} detected videos")
    if t.get('combined_views'): p.append(f"{t['combined_views']:,} combined views")
    if t.get('avg_views'): p.append(f"{t['avg_views']:,} average views")
    return ' | '.join(p) or 'trend signal detected'


def sources(t: dict[str, Any], videos: list[dict[str,str]]) -> list[dict[str,str]]:
    words=[w.lower() for w in re.findall(r'[A-Za-z0-9]+',t['trend']) if len(w)>3]
    out=[]
    for v in videos:
        if words and any(w in v['title'].lower() for w in words):
            out.append(v)
        if len(out)>=3: break
    return out


def trend_reason(t: dict[str,Any], region: str) -> str:
    g=infer_genre(t); name=t['trend']
    reasons={
      'Thriller':'unanswered questions and delayed answers naturally create retention because viewers want the next clue.',
      'Crime':'the viewer becomes a detective: evidence, suspects, contradictions and a final answer create participation.',
      'Mystery':'the strongest mechanism is a solvable question where the audience can form a theory before the reveal.',
      'Comedy':'the click comes from a simple premise with an unpredictable consequence, not from random jokes.',
      'Horror':'anticipation plus uncertainty keeps viewers waiting for the exact moment the threat becomes clear.',
      'Gaming':'gameplay becomes stronger when there is a mission, rule, consequence or mystery instead of raw gameplay.',
      'Technology':'the best angle is an unexpected result from a familiar tool, creating a test the viewer wants to see finished.',
      'Challenge':'a clear rule and measurable outcome give the audience a reason to stay until the result.',
    }
    base=reasons.get(g,'the topic has audience attention, but the creator opportunity is to turn it into a specific question, conflict or transformation.')
    return f"{region} trend: {name}. {base} The opportunity is to build a story around the trend rather than simply report it. Signal: {stats(t)}."


def idea(rank,title,hook,premise,genre,fmt,structure,why,trend_basis='',src=None,region='India + World'):
    steps=[x.strip() for x in structure.split('→') if x.strip()]
    payoff=steps[-1] if steps else 'the final reveal'
    return {
      'rank':rank,'high_ctr_idea':title,'title':title,'hook':hook,'format':fmt,'genre':genre,'region':region,
      'why_people_will_click':why,'story_premise':premise,'story_engine':' → '.join(steps),
      'first_15_seconds':f"0–3 sec: {hook} 3–8 sec: establish the unanswered question. 8–15 sec: reveal the first piece of evidence without explaining it.",
      'escalation':' → '.join(steps),'payoff':payoff,
      'thumbnail_concept':'One face/emotion + one impossible visual clue + 2–4 curiosity words. Do not repeat the title.',
      'logline_roman_telugu':(
          f"Start lo {premise.lower()} ani audience ki anipistundi. Kani madhyalo oka strong clue dorukutundi; dani valla {genre.lower()} angle lo asalu problem vere laga kanipistundi. Prathi step tho tension perigela clues ivvali, audience kuda answer guess cheyyali. Last lo {payoff.lower()} reveal ayyaka opening lo unna small detail ki kotha meaning vastundi — ade satisfying payoff."
      ),
      'trend_basis':trend_basis or 'Original concept','source_videos':src or [],
      'ctr_score':9.0 if any(w in title.lower() for w in ['nobody','wrong','impossible','one','last','before','why','secret','missing']) else 8.7,
    }


SHORT_BLUEPRINTS=[
 ('The Trend Is Not What You Think — Watch The Last 5 Seconds','Start with the familiar trend, then expose one detail that changes its meaning.','familiar trend → overlooked clue → contradiction → reveal'),
 ('Everyone Saw This. Almost Nobody Noticed The Real Clue.','Make one tiny visual detail the key to a much bigger question.','observation → clue → false theory → proof → reveal'),
 ('I Tried The Trend Once. Then The Unexpected Thing Happened.','The trend is only the setup; the unexpected consequence is the actual story.','attempt → failure → consequence → escalation → payoff'),
 ('You Get One Guess Before I Reveal What Really Happened','Give the viewer enough evidence to form a theory, then destroy the obvious answer.','question → 2 clues → audience guess → contradiction → reveal'),
 ('The Last 3 Seconds Change Everything You Just Watched','Plant a clue early that becomes meaningful only after the ending.','normal scene → strange detail → escalation → final reversal'),
 ('I Found The One Detail Everyone Else Ignored','Turn an overlooked detail from the current topic into a mini investigation.','detail → why it matters → evidence → reveal'),
 ('I Thought I Knew Why This Was Trending. I Was Wrong.','Start with the obvious explanation and prove why it is incomplete.','assumption → test → contradiction → new answer'),
 ('One Rule. One Attempt. If I Fail, The Video Ends.','A strict rule creates immediate stakes and makes every action meaningful.','rule → temptation → near failure → final attempt → result'),
]

LONG_BLUEPRINTS=[
 ('The Trend Everyone Is Copying Has One Problem Nobody Talks About','Investigate the hidden weakness behind the popular format and prove it with examples.','popular belief → evidence → test → failure → conclusion'),
 ('Why This Trend Exploded — The Real Reason Is Not What You Think','Find the emotional or structural reason behind the spike and test the theory.','trend → obvious reason → competing theory → evidence → verdict'),
 ('I Tried To Recreate The Trend Under One Impossible Rule','Make the audience wait for a measurable final result.','goal → rule → attempt 1 → failure → escalation → final attempt → result'),
 ('I Found A Mystery Hidden Inside A Viral Trend','Use the trend as evidence in a story the audience can solve with you.','question → clue 1 → false lead → clue 2 → contradiction → reveal'),
 ('What If The Trend Is Popular For The Wrong Reason?','Challenge the obvious explanation and build a stronger explanation from evidence.','popular explanation → alternative theory → tests → proof → payoff'),
 ('I Built A Video Around The One Detail Everyone Ignores','Turn a small overlooked detail into the central mystery of the episode.','ignored detail → why ignored → evidence → escalation → payoff'),
 ('I Tried To Predict What Would Happen Before The Trend Did','Make a prediction early, then spend the video trying to prove or destroy it.','prediction → clues → tests → near-proof → final result'),
 ('The Trend Looks Simple. Recreating It Was Not.','A production challenge with visible failures and a final comparison.','simple promise → preparation → failures → breakthrough → result'),
]

GENERAL_SHORTS=[
 ('My Camera Recorded Something I Never Saw','A solo creator notices one impossible-looking detail in yesterday’s footage.','normal footage → strange frame → investigation → reveal','Psychological Thriller'),
 ('Someone Sent Me A Photo Taken From Inside My Room','An impossible photo creates a question about when and how it was taken.','message → photo → timestamp → physical clue → reveal','Mystery Thriller'),
 ('The Message Arrived Before I Did','A message appears to predict an action seconds before it happens.','message → prediction → test → pattern → twist','Psychological Thriller'),
 ('I Found My Own Missing Video On A Stranger’s Phone','A missing file becomes a physical mystery with a final explanation.','missing file → discovery → contradiction → clue → payoff','Tech Mystery'),
 ('The Lift Stopped On A Floor That Does Not Exist','A normal location becomes a mystery through one impossible event.','routine → impossible event → exploration → clue → reveal','Mystery Thriller'),
 ('I Heard Tomorrow’s News Tonight','A fictional future recording contains a detail that appears moments later.','recording → prediction → verification → escalation → reveal','Psychological Thriller'),
 ('The Same Stranger Appeared In Every Video','A repeated background figure turns unrelated footage into one connected mystery.','observation → repeated figure → pattern → investigation → reveal','Mystery'),
 ('I Deleted The File. It Came Back With A New Timestamp.','A digital glitch becomes evidence of a bigger mystery.','deletion → return → timestamp → physical clue → payoff','Tech Thriller'),
]

GENERAL_LONG=[
 ('I Tried To Solve A Mystery Using Only What My Camera Saw','Investigate a staged mystery using only existing footage while the audience gets the evidence too.','Crime-Mystery'),
 ('I Had 8 Minutes To Prove Someone Was Lying','One claim, three pieces of evidence and a final contradiction drive the story.','Psychological Thriller'),
 ('I Followed A Set Of Instructions I Found In My Own Room','Each harmless instruction creates the next clue until the original source is revealed.','Mystery Thriller'),
 ('I Made A Mystery Where The Audience Gets The Answer First','Show the crucial clue early, then make viewers doubt what they saw.','Mystery'),
 ('I Tried To Reconstruct A Missing 10 Minutes','Timestamps, objects and inconsistencies reconstruct an unexplained gap.','Psychological Mystery'),
 ('Every Clue Pointed To The Wrong Person','The obvious suspect looks guilty until one final clue changes the timeline.','Crime-Mystery'),
 ('I Turned One Ordinary Night Into A Crime Investigation','An everyday event gradually becomes a case with evidence and a reveal.','Crime-Thriller'),
 ('I Tested Whether A Stranger Could Predict My Next Move','A controlled prediction experiment escalates until one result cannot be easily explained.','Psychological Thriller'),
]

FUSIONS=[
 ('Thriller + Comedy','A funny character accidentally becomes the only person who notices a serious clue.','Comedy misdirection → real clue → danger → reveal','The emotional switch from laughter to genuine stakes creates novelty.'),
 ('Crime + Technology','A tiny digital inconsistency becomes the clue that exposes the entire timeline.','digital clue → false explanation → evidence → reveal','Technology gives the crime story a concrete evidence trail.'),
 ('Mystery + Challenge','The creator has a strict countdown while solving clues the audience can also see.','countdown → clues → false lead → final clue → reveal','The countdown adds pressure while the mystery makes viewers participate.'),
 ('Psychological Thriller + Comedy','A harmless joke becomes disturbing when the same prediction keeps coming true.','joke → coincidence → test → pattern → payoff','The genre switch creates surprise without needing expensive production.'),
 ('Horror + Technology','A familiar phone feature becomes the mechanism for discovering something impossible.','normal feature → anomaly → investigation → reveal','The familiar technology makes the impossible event feel close to the viewer.'),
 ('Gaming + Thriller','A game event begins appearing outside the game through connected clues.','game clue → real clue → escalation → connection → reveal','The virtual/real boundary creates a strong curiosity gap.'),
 ('Crime + Comedy','The person everyone ignores solves the case because they notice what experts dismiss.','comic observation → serious clue → mistaken theory → solution','Comedy gives the character an unusual way of seeing the evidence.'),
 ('Mystery + Technology','An ordinary app appears to know something it could not know.','prediction → test → impossible result → investigation → reveal','The app becomes a story engine rather than a gimmick.'),
]


def trend_analysis(trends,videos,region):
    out=[]
    for i in range(IDEAS_PER_SECTION):
        t=trends[i%len(trends)] if trends else {'trend':'current audience curiosity','subgenre':'Mystery','mentions':0,'combined_views':0,'avg_views':0,'category':''}
        name=t['trend']; g=infer_genre(t)
        modes=[
          (f'Why {name} Is Winning YouTube Right Now — And The Story Angle Nobody Is Using',f'{name} is getting attention. The real question is why viewers choose it now and what story angle has not been claimed yet.','visible trend → audience reason → hidden mechanism → creator angle → payoff'),
          (f'{name}: The Exact Moment A Viewer Decides To Keep Watching',f'Break the trend into its hook, emotional promise and retention mechanism instead of merely describing it.','example → hook → retention mechanism → proof → creator formula'),
          (f'The {g} Side Of {name} Is Bigger Than The Trend Itself',f'Map the trend into {g} and identify a creator-friendly story structure that can be made original.','trend → genre split → audience emotion → winning structure → opportunity'),
          (f'Everyone Sees {name}. Few Understand Why It Gets Clicks.',f'Reverse-engineer the topic into title promise, thumbnail promise, opening tension and payoff.','surface trend → click trigger → retention trigger → mistake → winning formula'),
        ]
        title,premise,structure=modes[i%4]
        out.append(idea(i+1,title,f'Open with the surprising consequence of {name}, not a definition of it.',premise,g,'Trend Analysis',structure,trend_reason(t,region),f"{name} | {stats(t)}",sources(t,videos),region))
    return out


def trend_shorts(trends,videos):
    out=[]
    for i,(title,premise,structure) in enumerate(SHORT_BLUEPRINTS):
        t=trends[i%len(trends)] if trends else {'trend':'current trend','subgenre':'Mystery','mentions':0,'combined_views':0,'avg_views':0}
        name=t['trend']; g=infer_genre(t)
        title=title.replace('The Trend',name)
        out.append(idea(i+1,title,f'Show the most surprising consequence connected to {name in title and name or "the trend"} in the first 3 seconds.',premise+f" Use {name} only as the topical entry point; the story must have its own conflict and payoff.",g,'YouTube Shorts',structure,'The trend supplies recognition; the new conflict supplies the reason to stay. This is not a copy of the trend.',f"Based on {name} | {stats(t)}",sources(t,videos)))
    return out


def trend_longform(trends,videos):
    out=[]
    for i,(title,premise,structure) in enumerate(LONG_BLUEPRINTS):
        t=trends[i%len(trends)] if trends else {'trend':'current trend','subgenre':'Mystery','mentions':0,'combined_views':0,'avg_views':0}
        name=t['trend']; g=infer_genre(t)
        title=title.replace('The Trend',name)
        out.append(idea(i+1,title,f'Show the result first, then promise to explain how it happened.',premise+f" Use {name} as the recognizable entry point, but make the episode a complete 8–10 minute story.",g,'YouTube Longform 8–10 min',structure,'It combines current-topic recognition with a real question, conflict and measurable payoff that can sustain 8–10 minutes.',f"Based on {name} | {stats(t)}",sources(t,videos)))
    return out


def general_shorts():
    out=[]
    for i,(title,premise,structure,genre) in enumerate(GENERAL_SHORTS[:IDEAS_PER_SECTION]):
        out.append(idea(i+1,title,'Start on the impossible moment. Do not begin with an introduction or explanation.',premise,genre,'YouTube Shorts',structure,'The premise creates a specific question immediately and delays the answer through evidence rather than empty suspense.'))
    return out


def general_longform():
    out=[]
    for i,(title,premise,g) in enumerate(GENERAL_LONG[:IDEAS_PER_SECTION]):
        out.append(idea(i+1,title,'Open on the strongest evidence or consequence, then cut back to before the problem started.',premise,g,'YouTube Longform 8–10 min','cold open → question → rules/evidence → false lead → escalation → final clue → reveal','Each section changes what the viewer thinks the answer is; it is a story, not a generic challenge.'))
    return out


def genre_fusion(trends):
    out=[]
    for i,(pair,premise,structure,why) in enumerate(FUSIONS):
        t=trends[i%len(trends)] if trends else {'trend':'current genre signal'}
        out.append(idea(i+1,[
          'The Funniest Person In The Room Notices The One Clue Everyone Missed',
          'The Digital Clue That Should Have Been Impossible',
          '10 Minutes. 8 Clues. One Answer Nobody Expects.',
          'I Made A Joke About It — Then The Prediction Came True',
          "My Phone Feature Revealed Something It Shouldn't Know",
          'The Game Gave Me A Clue That Existed In Real Life',
          'The Worst Detective In The Room Solved The Case',
          'The App Predicted Something I Hadn’t Done Yet',
        ][i],f'Use {pair} to create two conflicting emotions: the viewer thinks they understand the scene, then the second genre changes its meaning.',premise+f" Trend wrapper: {t.get('trend','current genre signal')}.",pair,'YouTube Longform 8–10 min',structure,why,f"Genre fusion + trend signal: {t.get('trend','current genre signal')}"))
    return out


def maybe_ai_refine(section_title, ideas):
    if not USE_OPENROUTER: return ideas
    key=os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENROUTER_KEY') or ''
    if not key: return ideas
    # One tiny refinement call only. Never let provider failure erase local ideas.
    payload={
      'model':OPENROUTER_MODEL,
      'messages':[{'role':'system','content':'You are a senior YouTube creative director. Return JSON only.'},{'role':'user','content':(
        'Improve these first 3 ideas for very high CTR. No silly/generic concepts. Keep concrete conflict, escalation, payoff and Roman Telugu logline. Do not invent facts. Return {"ideas":[{"rank":1,"title":"...","hook":"...","why_people_will_click":"...","logline_roman_telugu":"..."}]}\nSECTION: '+section_title+'\n'+json.dumps(ideas[:3],ensure_ascii=False)
      )}],
      'temperature':0.9,'max_tokens':OPENROUTER_MAX_TOKENS
    }
    try:
      r=requests.post(OPENROUTER_URL,headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},json=payload,timeout=40)
      if r.status_code!=200: return ideas
      content=(r.json().get('choices') or [{}])[0].get('message',{}).get('content','')
      m=re.search(r'\{.*\}',content,re.S)
      if not m: return ideas
      improved=json.loads(m.group(0)).get('ideas',[])
      byrank={x.get('rank'):x for x in improved if isinstance(x,dict)}
      for x in ideas:
        y=byrank.get(x['rank'])
        if y:
          for k in ('title','hook','why_people_will_click','logline_roman_telugu'):
            if clean(y.get(k)): x[k]=clean(y[k])
    except Exception as e:
      print(f'[WARN] AI refinement skipped: {e}')
    return ideas


def generate_report(*args,**kwargs):
    india=kwargs.get('india_trends') or kwargs.get('india_data') or kwargs.get('india')
    world=kwargs.get('world_trends') or kwargs.get('world_data') or kwargs.get('world')
    if india is None and args: india=args[0]
    if world is None and len(args)>1: world=args[1]
    if india is None: india=kwargs.get('data') or kwargs.get('trend_data') or kwargs.get('videos') or {}
    if world is None: world={}
    iv=extract_videos(india,80); wv=extract_videos(world,80)
    it=extract_trends(india,40); wt=extract_trends(world,40)
    alltr=[]; seen=set()
    for t in it+wt:
        if t['trend'].lower() not in seen:
            seen.add(t['trend'].lower()); alltr.append(t)
    if not it: it=alltr[:]
    if not wt: wt=alltr[:]
    print(f'[INFO] India trends={len(it)} World trends={len(wt)} Videos={len(iv)+len(wv)}')
    sections={
      'india_trends':{'title':'1. India YouTube Trends','ideas':trend_analysis(it,iv,'India')},
      'world_trends':{'title':'2. World YouTube Trends','ideas':trend_analysis(wt,wv,'World')},
      'genre_trends':{'title':'3. YouTube Genre Trends','ideas':trend_analysis(alltr,iv+wv,'India + World')},
      'trend_shorts':{'title':'4. Trend-Based Shorts Ideas','ideas':trend_shorts(alltr,iv+wv)},
      'trend_longform':{'title':'5. Trend-Based Longform Ideas','ideas':trend_longform(alltr,iv+wv)},
      'general_shorts':{'title':'6. General India + World Shorts Ideas','ideas':general_shorts()},
      'general_longform':{'title':'7. General India + World Longform Ideas','ideas':general_longform()},
      'genre_fusion':{'title':'8. Genre-Fusion High-CTR Ideas','ideas':genre_fusion(alltr)},
    }
    for k,s in sections.items(): s['ideas']=maybe_ai_refine(s['title'],s['ideas'])
    return {'title':'YOUTUBE HIGH CTR IDEA GENERATOR','generated_at':datetime.now(timezone.utc).astimezone().isoformat(),'ideas_per_section':IDEAS_PER_SECTION,'engine':'High-CTR Story Engine + optional OpenRouter refinement','sections':sections}


def render_report(report,output_path=None):
    if isinstance(report,str): text=report
    else:
      lines=['='*78,'YOUTUBE HIGH CTR IDEA GENERATOR','='*78,f"Generated: {report.get('generated_at','')}",f"Ideas per section: {report.get('ideas_per_section',8)}",'','QUALITY STANDARD: Concrete premise + curiosity gap + conflict + escalation + payoff.','']
      for key,title in SECTIONS:
        sec=report['sections'].get(key,{})
        lines += ['','='*78,sec.get('title',title),'='*78,'']
        for x in sec.get('ideas',[]):
          lines += [f"#{x['rank']} HIGH CTR IDEA",'-'*78,f"High CTR Idea: {x['high_ctr_idea']}",'',f"Hook: {x['hook']}",'',f"Format: {x['format']}",f"Genre: {x['genre']}",f"Region: {x.get('region','India + World')}",f"CTR Score: {x.get('ctr_score','')}/10",'', 'WHY PEOPLE WILL CLICK:',x['why_people_will_click'],'','STORY PREMISE:',x['story_premise'],'','FIRST 15 SECONDS:',x['first_15_seconds'],'','ESCALATION:',x['escalation'],'','PAYOFF:',x['payoff'],'','THUMBNAIL CONCEPT:',x['thumbnail_concept'],'','ROMAN TELUGU LOGLINE:',x['logline_roman_telugu'],'','TREND BASIS:',x['trend_basis'],'']
          if x.get('source_videos'):
            lines += ['SOURCE VIDEOS:']+[f"- {v['title']}" + (f" | {v['url']}" if v.get('url') else '') for v in x['source_videos']]+['']
      lines += ['','='*78,'END OF REPORT','='*78]
      text='\n'.join(lines)
    if output_path:
      p=Path(output_path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding='utf-8')
    return text


def save_json(report,path=None):
    p=Path(path or OUTPUT_DIR/'youtube_high_ctr_ideas.json'); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); return p


def save_txt(report,path=None):
    p=Path(path or OUTPUT_DIR/'youtube_high_ctr_report.txt'); render_report(report,p); return p


if __name__=='__main__':
    demo={'india':{'longform':[{'trend':'Trailer','mentions':15,'combined_views':35908591,'avg_views':2393906,'category':'Entertainment','subgenre':'Movies & Entertainment'},{'trend':'Crime Investigation','mentions':9,'combined_views':18000000,'avg_views':2000000,'category':'Entertainment','subgenre':'Crime Thriller'}]},'world':{'longform':[{'trend':'AI Experiment','mentions':12,'combined_views':30000000,'avg_views':2500000,'category':'Technology','subgenre':'Technology'}]}}
    r=generate_report(india_trends=demo['india'],world_trends=demo['world'])
    print(save_txt(r)); print(save_json(r)); print('[OK] 8 sections x 8 ideas generated')
