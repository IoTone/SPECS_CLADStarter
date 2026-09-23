const fs = require('fs');
const path = require('path');
const audio = require('/Users/dkords/.codex/plugins/cache/ls-extensions/ls-clad/local/skills/build-sfx/tools');
const PROJECT_ASSETS_SFX = '/Users/dkords/dev/projects/iotone/SPECS_CladStarter/Assets/GeneratedSFX';
fs.mkdirSync(PROJECT_ASSETS_SFX, {recursive:true});
for (const [name, buffer] of [
 ['CastleShield', audio.sfx_presets.impact({material:'metal',size:0.3})],
 ['CastleStone', audio.sfx_presets.impact({material:'stone',size:0.5})],
 ['CastleWin', audio.sfx_presets.uiSuccess()]
]) {
 audio.mix_bus.masterChain(buffer,{normalize:'peak'});
 audio.WavBuilder.write(buffer,path.join(PROJECT_ASSETS_SFX,name+'.wav'));
 console.log(name,fs.statSync(path.join(PROJECT_ASSETS_SFX,name+'.wav')).size);
}
