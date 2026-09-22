const fs=require('fs'), path=require('path');
const a=require('/Users/dkords/.codex/plugins/cache/ls-extensions/ls-clad/local/skills/build-sfx/tools');
const m=require('/Users/dkords/.codex/plugins/cache/ls-extensions/ls-clad/local/skills/build-music/tools');
const out='/Users/dkords/dev/projects/iotone/SPECS_CladStarter/Assets/GeneratedSFX';
fs.mkdirSync(out,{recursive:true});
for(const [name,b] of [['PlasticImpact',a.sfx_presets.impact({material:'soft',size:0.3})],['BallOut',a.sfx_presets.uiPop({pitch:3})],['Victory',a.sfx_presets.uiSuccess()]]) {a.mix_bus.masterChain(b,{normalize:'peak'});a.WavBuilder.write(b,path.join(out,name+'.wav'));}
const {chords,meta}=m.composeChords({genre:'pop',voice:'kalimba',scale:'major'});const bpm=m.suggestTempo('pop');console.log(meta,bpm);
const comp=m.chordEvents(chords,{voice:'kalimba',bars:8,velocity:58});
const bass=m.composeBass({chords,genre:'pop',bars:8});
const tracks=[m.track('kalimba','kalimba',comp,{fx:{hpf:260,lpf:4200,reverb:'smallRoom',gain:0.42}}),m.track('bass','subBass',m.mask(bass,m.arrangement.arrangement8().a,8,4),{fx:{lpf:220,gain:0.25}})];
const music=m.render(tracks,{bpm,master:{normalize:'peak',glue:true,width:1.1}});m.WavBuilder.write(music,path.join(out,'BackgroundMusic.wav'));
