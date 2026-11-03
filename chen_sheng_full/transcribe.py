#!/usr/bin/env python3
"""ASR timing audit for the original 402.12-second Thai narration."""
from pathlib import Path
import json, subprocess
from faster_whisper import WhisperModel
ROOT=Path("chen_sheng_full"); AS=ROOT/"assets"; OUT=ROOT/"timing"
OUT.mkdir(parents=True,exist_ok=True)
AUDIO=OUT/"narration.wav"
# Recombine exact ordered AAC byte chunks; decode to 24k PCM for stable model input.
source=OUT/"narration.aac"
with source.open("wb") as dst:
 for p in sorted(AS.glob("audio.part*")):dst.write(p.read_bytes())
subprocess.check_call(["ffmpeg","-y","-v","error","-i",str(source),"-ar","24000","-ac","1","-t","402.12",str(AUDIO)])
model=WhisperModel("base",device="cpu",compute_type="int8",cpu_threads=4)
segments,info=model.transcribe(str(AUDIO),language="th",beam_size=5,vad_filter=True,word_timestamps=True)
all_segments=[];all_words=[]
for s in segments:
 row={"start":s.start,"end":s.end,"text":s.text,"avg_logprob":s.avg_logprob,"no_speech_prob":s.no_speech_prob}
 all_segments.append(row)
 for w in s.words or []: all_words.append({"start":w.start,"end":w.end,"text":w.word,"probability":w.probability})
def ts(t):
 ms=round(t*1000);h,rem=divmod(ms,3600000);m,rem=divmod(rem,60000);s,ms=divmod(rem,1000)
 return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
srt=[]
for i,v in enumerate(all_segments,1):
 srt.extend([str(i),ts(v["start"])+" --> "+ts(v["end"]),v["text"].strip(),""])
(OUT/"asr_draft.srt").write_text("\n".join(srt),encoding="utf8")
(OUT/"asr_segments.json").write_text(json.dumps({"duration_source_sec":402.12,"language":"th","segments":all_segments,"words":all_words},ensure_ascii=False,indent=2),encoding="utf8")
print(json.dumps({"segment_count":len(all_segments),"word_count":len(all_words),"first":all_segments[:3],"last":all_segments[-2:]},ensure_ascii=False),flush=True)
