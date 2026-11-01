#!/usr/bin/env python3
"""Snapshot an ADT's integration contracts; compare a repaired copy without a browser."""
import argparse
from collections import Counter
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re

VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[]; self.nodes=[]; self.images=[]; self.controls=[]
        self.meta=[]; self.scripts=[]; self.answers=[]; self.links=[]; self.types=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        n={'tag':tag,'attrs':a,'text':[],'child_id':False}
        if a.get('data-id'):
            for parent in self.stack:
                if parent['attrs'].get('data-id'): parent['child_id']=True
        self.nodes.append(n)
        if tag not in VOID: self.stack.append(n)
        if tag=='img': self.images.append({'id':a.get('data-id'),'src':a.get('src'),'alt':a.get('alt')})
        if tag in {'input','textarea','select'}:
            self.controls.append({k:a.get(k) for k in ['id','type','name','value','data-activity-item','data-aria-id']}|{'tag':tag})
        if tag=='meta' and a.get('name'): self.meta.append([a['name'],a.get('content')])
        if tag=='script' and a.get('src'): self.scripts.append(a['src'])
        if 'data-correct-answers' in a or 'data-option-explanations' in a:
            self.answers.append({k:a[k] for k in ['data-correct-answers','data-option-explanations'] if k in a})
        if tag=='a' and a.get('href'): self.links.append(a['href'])
        if a.get('data-section-type'): self.types.append(a['data-section-type'])
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in VOID:self.handle_endtag(tag)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i]['tag']==tag:
                del self.stack[i:]
                break
    def handle_data(self,text):
        for n in self.stack:n['text'].append(text)
    def result(self):
        texts=[{'id':n['attrs']['data-id'],'text':' '.join(''.join(n['text']).split())}
               for n in self.nodes if n['attrs'].get('data-id') and not n['child_id'] and n['tag']!='img']
        scripts=[{'id':n['attrs'].get('id'),'text':''.join(n['text']).strip()}
                 for n in self.nodes if n['tag']=='script' and n['attrs'].get('type')=='application/json']
        return dict(texts=texts,images=self.images,controls=self.controls,meta=self.meta,
                    scripts=self.scripts,answers=self.answers,answer_scripts=scripts,
                    links=self.links,section_types=self.types)

def snapshot(root,pdf=None):
    root=root.resolve();spine=json.loads((root/'content/pages.json').read_text())
    pages=[]
    for entry in spine:
        f=(root/entry['href']).resolve()
        if not f.is_relative_to(root):raise ValueError('Page escapes ADT root: '+entry['href'])
        scanner=Page();scanner.feed(f.read_text())
        m=re.match(r'pg(\d+)_',f.name)
        pages.append({'href':entry['href'],'source_page_hint':int(m[1]) if m else None,
                      'sha256':digest(f),**scanner.result()})
    file_hashes={str(f.relative_to(root)):digest(f) for f in sorted(root.rglob('*')) if f.is_file() and not f.is_symlink()}
    missing=[];remote=[]
    for row in pages:
        for image in row['images']:
            src=image['src'] or ''
            if re.match(r'^(?:https?:|//|data:)',src):remote.append(src)
            elif not (root/row['href']).parent.joinpath(src.split('?')[0]).is_file():missing.append({'page':row['href'],'src':src})
    data={'schema_version':1,'root':str(root),'spine':spine,'pages':pages,'files':file_hashes,
          'missing_images':missing,'nonlocal_images':sorted(set(remote)),
          'summary':{'sections':len(pages),'controls':sum(len(r['controls']) for r in pages),
                     'source_page_hints':sorted({r['source_page_hint'] for r in pages if r['source_page_hint']})}}
    if pdf:
        try:from pypdf import PdfReader
        except ImportError:raise SystemExit('--pdf needs pypdf in the selected Python runtime.')
        count=len(PdfReader(str(pdf)).pages)
        represented=set(data['summary']['source_page_hints'])
        data['pdf']={'path':str(pdf.resolve()),'sha256':digest(pdf),'physical_pages':count,
                     'unmatched_page_hints':sorted(set(range(1,count+1))-represented),
                     'note':'Filename hints require visual verification; unmatched pages may be represented within another section.'}
    return data

def compare(before,after,allowed):
    issues=[];exceptions=[]
    def issue(path,message):
        (exceptions if path in allowed else issues).append({'path':path,'message':message})
    if before['spine']!=after['spine']:issue('content/pages.json','Navigation spine changed')
    new={r['href']:r for r in after['pages']}
    for old in before['pages']:
        name=old['href'];current=new.get(name)
        if not current:issue(name,'Section missing');continue
        for field in ['meta','answers','answer_scripts','links','section_types']:
            if old[field]!=current[field]:issue(name,'Changed '+field)
        old_scripts=iter(current['scripts'])
        if not all(any(script==candidate for candidate in old_scripts) for script in old['scripts']):
            issue(name,'Removed or reordered existing script identity')
        for field in ['texts','controls']:
            counts=Counter(json.dumps(x,sort_keys=True,ensure_ascii=False) for x in current[field])
            for item in old[field]:
                key=json.dumps(item,sort_keys=True,ensure_ascii=False)
                if counts[key]:counts[key]-=1
                else:issue(name,'Missing or changed '+field+': '+key)
        for image in old['images']:
            if not any(image['id']==x['id'] and image['src']==x['src'] for x in current['images']):issue(name,'Missing image binding: '+str(image))
    for name,sha in before['files'].items():
        protected=(name=='index.html' or name.startswith('content/') or name.startswith('assets/'))
        if protected and after['files'].get(name)!=sha:issue(name,'Protected file changed or missing')
    if after['missing_images']:issues.extend({'path':x['page'],'message':'Missing image '+x['src']} for x in after['missing_images'])
    return {'passed':not issues,'issues':issues,'explicit_exceptions':exceptions,'allowed_paths':sorted(allowed)}

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--adt',type=Path,required=True);a.add_argument('--pdf',type=Path)
    a.add_argument('--out',type=Path,required=True);a.add_argument('--compare',type=Path)
    a.add_argument('--allow-change',action='append',default=[])
    args=a.parse_args();data=snapshot(args.adt,args.pdf)
    if args.compare:data['comparison']=compare(json.loads(args.compare.read_text()),data,set(args.allow_change))
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'summary':data['summary'],'comparison':data.get('comparison'),'out':str(args.out)},ensure_ascii=False))
    if data.get('comparison',{}).get('passed') is False:raise SystemExit(1)

if __name__=='__main__':main()
