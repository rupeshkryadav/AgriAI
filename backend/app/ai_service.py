import asyncio
import io
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
GEMINI_KEY_ERROR='Gemini API Key is missing or invalid in backend/.env'
AGRICULTURE_SYSTEM_PROMPT=(
    'You are FarmerConnect, an agricultural extension assistant for farmers in India. '
    'Give evidence-based, practical crop guidance in the requested language. Ask brief follow-up questions if crop, '
    'region, growth stage, or symptoms are needed. Never invent prices, pesticide products, or dosage. For chemical '
    'options, provide only label-consistent active ingredients and direct the farmer to follow the exact local product '
    'label, protective equipment, pre-harvest interval, and local KVK/agronomist guidance.'
)

def _client():
    key=os.getenv('GEMINI_API_KEY','').strip()
    if not key: raise HTTPException(500,GEMINI_KEY_ERROR)
    try:
        from google import genai
        from google.genai import types
        options=types.HttpOptions(
            timeout=int(os.getenv('GEMINI_TIMEOUT_MS','45000')),
            retry_options=types.HttpRetryOptions(attempts=int(os.getenv('GEMINI_RETRY_ATTEMPTS','1'))),
        )
        return genai.Client(api_key=key,http_options=options)
    except Exception as exc:
        raise HTTPException(500,'Google GenAI SDK could not initialize. Check backend dependencies.') from exc

def _generate(contents, system_prompt):
    from google.genai import types
    model=os.getenv('GEMINI_MODEL','gemini-3.8-flash').strip()
    fallbacks=[x.strip() for x in os.getenv('GEMINI_FALLBACK_MODELS','gemini-3.6-flash').split(',') if x.strip() and x.strip()!=model]
    client=_client()
    try:
        for index,candidate in enumerate([model,*fallbacks]):
            try:
                result=client.models.generate_content(
                    model=candidate,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.25,
                        max_output_tokens=1400,
                    ),
                )
                if not result.text: raise HTTPException(502,'Gemini returned an empty response.')
                return result.text
            except HTTPException:
                raise
            except Exception as exc:
                status=getattr(exc,'status_code',None) or getattr(exc,'code',None)
                response=getattr(exc,'response',None)
                status=status or getattr(response,'status_code',None)
                message=str(exc).lower()
                if status in (401,403) or 'api key not valid' in message or 'invalid api key' in message or 'api_key_invalid' in message:
                    raise HTTPException(401,GEMINI_KEY_ERROR) from exc
                if index<len(fallbacks) and (status in (404,429,500,502,503,504) or re.search(r'\b(404|429|500|502|503|504)\b',message)):
                    continue
                raise HTTPException(502,'Gemini request failed. Verify backend connectivity and the configured Gemini model.') from exc
        raise HTTPException(503,'All configured Gemini models are temporarily unavailable.')
    finally:
        client.close()

def _local_leaf_prediction(raw):
    weights=ROOT/'ml'/'crop_doctor_model.pt'
    classes=ROOT/'ml'/'class_indices.json'
    if not weights.is_file() or not classes.is_file(): return None
    try:
        import torch
        from torch import nn
        from torchvision import models, transforms
        names=json.loads(classes.read_text(encoding='utf-8'))
        model=models.mobilenet_v3_small(weights=None)
        model.classifier[3]=nn.Linear(model.classifier[3].in_features,len(names))
        model.load_state_dict(torch.load(weights,map_location='cpu',weights_only=True));model.eval()
        image=Image.open(io.BytesIO(raw)).convert('RGB')
        tensor=transforms.Compose([transforms.Resize((224,224)),transforms.ToTensor(),transforms.Normalize([.485,.456,.406],[.229,.224,.225])])(image).unsqueeze(0)
        with torch.no_grad(): probabilities=torch.softmax(model(tensor),1)[0]
        index=int(probabilities.argmax())
        return {'disease':list(names.keys())[index],'confidence':round(float(probabilities[index])*100,1),'source':'local_mobilenet_v3'}
    except Exception:
        return None

async def diagnose_leaf(raw:bytes,mime_type:str,language:str='English'):
    local=_local_leaf_prediction(raw)
    hint=(f"A local image model suggested {local['disease']} at {local['confidence']}% confidence. Treat it only as a secondary clue. " if local else '')
    prompt=(f'Analyze this crop leaf photograph and respond in {language}. {hint}'
            'Give: (1) likely disease or say it cannot be identified, with visual evidence and uncertainty; '
            '(2) severity as low, moderate, or high and why; (3) immediate field actions; '
            '(4) actionable organic treatment and prevention; (5) chemical treatment options only if reliable for this crop, '
            'with clear instruction to follow the locally registered product label. Do not guess dose. '
            'If image quality is insufficient, request a clearer close-up. State that photo screening is not lab confirmation.')
    from google.genai import types
    result=await asyncio.to_thread(_generate,[prompt,types.Part.from_bytes(data=raw,mime_type=mime_type)],f'{AGRICULTURE_SYSTEM_PROMPT} Respond in {language}.')
    return {'disease':local['disease'] if local else 'Gemini visual diagnosis','confidence':local['confidence'] if local else None,'classifier':local['source'] if local else 'gemini_vision','diagnosis':result,'advice':result,'language':language,'disclaimer':'Photo screening is advisory and is not a laboratory diagnosis.'}

async def chat_with_gemini(message:str,language:str='English',history=None):
    from google.genai import types
    contents=[]
    for turn in (history or [])[-20:]:
        role=turn.get('role')
        text=turn.get('text')
        if role in ('user','model') and isinstance(text,str) and text.strip():
            contents.append(types.Content(role=role,parts=[types.Part.from_text(text=text[:3000])]))
    contents.append(types.Content(role='user',parts=[types.Part.from_text(text=message)]))
    result=await asyncio.to_thread(_generate,contents,f'{AGRICULTURE_SYSTEM_PROMPT} Answer in {language}.')
    return {'reply':result,'language':language,'available':True}
