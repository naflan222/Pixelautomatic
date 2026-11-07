"""Original procedural ambient groove; no downloaded recordings or copyrighted songs."""
import math
import random
import wave
from array import array
from pathlib import Path


def create_soundtrack(path, seed=0, duration=20, sample_rate=44100):
    rng=random.Random(seed)
    chords=[(146.832,174.614,220.0),(130.813,164.814,195.998),(110.0,130.813,164.814),(130.813,174.614,220.0),(146.832,174.614,220.0)]
    beat=60/96
    samples=array('f')
    for i in range(int(duration*sample_rate)):
        t=i/sample_rate
        chord=chords[min(4,int(t/4))]
        phase=t%4
        swell=min(1,phase/.45)*min(1,(4-phase)/.65)
        pad=sum(math.sin(2*math.pi*f*t)+.22*math.sin(2*math.pi*f*2*t) for f in chord)*.075*swell
        b=t%beat
        kick=.20*math.sin(2*math.pi*(48*b+9*(1-math.exp(-b*30))))*math.exp(-b*19)
        hat=(rng.random()*2-1)*.024*math.exp(-(t%(beat/2))*65)
        bass=.09*math.sin(2*math.pi*chord[0]/2*t)*math.exp(-b*4)
        pluck_t=t%(beat*2)
        note=chord[int(t/(beat*2))%3]*2
        pluck=.065*(math.sin(2*math.pi*note*t)+.2*math.sin(2*math.pi*note*3*t))*math.exp(-pluck_t*5)
        fade=min(1,t/.6,max(0,(duration-t)/1.2))
        samples.append((pad+kick+hat+bass+pluck)*fade)
    peak=max(abs(v) for v in samples) or 1
    pcm=array('h')
    for i,v in enumerate(samples):
        # Subtle stereo delay widens the original score, while keeping mono compatibility.
        right=.91*v+.09*(samples[i-661] if i>=661 else 0)
        pcm.extend((int(v/peak*23500),int(right/peak*23500)))
    import sys
    if sys.byteorder!='little':pcm.byteswap()
    path=Path(path)
    with wave.open(str(path),'wb') as out:
        out.setnchannels(2);out.setsampwidth(2);out.setframerate(sample_rate);out.writeframes(pcm.tobytes())
    return path
