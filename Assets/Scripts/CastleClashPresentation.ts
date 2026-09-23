/** Owns only procedural visuals and confirmed-hit audio, never gameplay. */
import {Snapshot,rail,walls} from './CastleClashSimulation';
import {Block,Color,meshObject} from './CastleClashGeometry';
const STONE:Color=[0.85,0.83,0.72,1],COPPER:Color=[0.9,0.57,0.29,1];
const TEAL:Color=[0.2,0.95,0.9,1],AMBER:Color=[1,0.7,0.2,1];
const SHIELD=requireAsset('../GeneratedSFX/CastleShield.wav') as AudioTrackAsset;
const STONE_SOUND=requireAsset('../GeneratedSFX/CastleStone.wav') as AudioTrackAsset;
const WIN=requireAsset('../GeneratedSFX/CastleWin.wav') as AudioTrackAsset;
export class CastleClashPresentation {
 private wallObjects:SceneObject[]=[];private shieldObjects:SceneObject[]=[];private crowns:SceneObject[]=[];private ball:SceneObject;private trail:SceneObject[]=[];private effects:SceneObject[]=[];private effectAge=10;private lastEvent=0;private audio:AudioComponent[]=[];
 constructor(private board:SceneObject,castleA:SceneObject,castleB:SceneObject,private material:Material,private shieldWidth:number,volume:number){
 const platform:Block[]=[[0,-0.9,0,42,1.8,62,[0.4,0.5,0.53,1]],[0,0.08,0,38,0.16,58,[0.58,0.66,0.63,1]]];
 for(const x of [-20,20])platform.push([x,0.5,0,1,1,60,COPPER]);for(const z of [-30,30])platform.push([0,0.5,z,40,1,1,COPPER]);
 for(let x=-16;x<=16;x+=8)for(let z=-24;z<=24;z+=8)platform.push([x,0.18,z,0.16,0.1,6,[0.72,0.76,0.7,1]]);
 meshObject(board,'Tournament board',platform,material);
 for(let side=0;side<2;side++){const root=side===0?castleA:castleB,c=side===0?TEAL:AMBER,k=side===0?1:-1;const blocks:Block[]=[];
 blocks.push([0,1.8,k*28.3,25.6,3.6,1.6,STONE]);
 for(const x of [-10,10]){blocks.push([x,3.4,k*26,3.6,6.8,3.6,STONE],[x,6.8,k*26,4.2,0.6,4.2,COPPER]);for(let i=0;i<4;i++)blocks.push([x+(i%2?1.4:-1.4),7.5,k*26+(i<2?-1.4:1.4),1,1.3,1,c]);}
 for(let p=0;p<54;p+=1){const q=rail(p,side);blocks.push([q.x,0.26,q.z,q.flank?0.18:1.05,0.18,q.flank?1.05:0.18,c]);}
 meshObject(root,'Towers and shield rail',blocks,material);
 const crown:Block[]=[[0,1.5,k*26,4.8,3,3.3,c],[0,3.3,k*26,5.3,0.8,3.7,COPPER]];for(let i=-1;i<=1;i++)crown.push([i*1.8,4.3,k*26,0.8,1.7,0.8,c]);this.crowns.push(meshObject(root,'Crown',crown,material));
 this.shieldObjects.push(meshObject(root,'Magic shield',[[0,2,0,shieldWidth,3.6,0.7,c],[0,2,0.05,shieldWidth-0.8,2.6,0.8,[0.9,1,1,1]]],material));
 }
 for(const w of walls()){const obj=meshObject(w.side===0?castleA:castleB,'Wall '+w.index,[[0,1.8,0,w.hx*2,3.6,w.hz*2,STONE],[0,3.8,0,w.hx*1.25,0.8,w.hz*1.25,COPPER]],material);obj.getTransform().setLocalPosition(new vec3(w.x,0,w.z));this.wallObjects.push(obj);}
 this.ball=meshObject(board,'Fireball',[[0,0,0,1.2,1.2,1.2,[1,0.95,0.5,1]]],material);
 for(let i=0;i<7;i++)this.trail.push(meshObject(board,'Ember trail '+i,[[0,0,0,0.65-i*0.05,0.65-i*0.05,0.65-i*0.05,[1,0.35+i*0.05,0.05,1]]],material));
 for(let i=0;i<8;i++){const o=meshObject(board,'Cosmetic rubble '+i,[[0,0,0,0.6,0.6,0.6,STONE]],material);o.enabled=false;this.effects.push(o);}
 for(const track of [SHIELD,STONE_SOUND,WIN]){const a=board.createComponent('Component.AudioComponent') as AudioComponent;a.audioTrack=track;a.volume=volume;a.playbackMode=Audio.PlaybackMode.LowLatency;this.audio.push(a);}
 }
 render(s:Snapshot,dt:number){
 for(let i=0;i<24;i++){const o=this.wallObjects[i];o.enabled=s.walls[i]>0;o.getTransform().setLocalScale(new vec3(1,s.walls[i]===1?0.63:1,1));}
 for(let side=0;side<2;side++){const q=rail(s.shields[side],side),o=this.shieldObjects[side];o.getTransform().setLocalPosition(new vec3(q.x,0,q.z));o.getTransform().setLocalRotation(quat.fromEulerAngles(0,q.flank?Math.PI/2:0,0));this.crowns[side].enabled=!(s.winner===1-side&&(s.phase==='round'||s.phase==='match'));}
 this.ball.getTransform().setLocalPosition(new vec3(s.x,2,s.z));this.ball.getTransform().setLocalRotation(quat.fromEulerAngles(getTime()*3,getTime()*4,0));
 for(let i=this.trail.length-1;i>=0;i--){const target=i===0?this.ball:this.trail[i-1];this.trail[i].enabled=s.phase==='playing';const t=this.trail[i].getTransform();t.setLocalPosition(vec3.lerp(t.getLocalPosition(),target.getTransform().getLocalPosition(),Math.min(1,dt*22)));}
 if(s.event!==this.lastEvent){this.lastEvent=s.event;this.audio[s.hit==='shield'?0:s.hit==='win'?2:1].play(1);this.effectAge=0;for(const e of this.effects)e.enabled=true;}
 this.effectAge+=dt;for(let i=0;i<this.effects.length;i++){const e=this.effects[i];e.enabled=this.effectAge<0.65;if(e.enabled){const a=i*Math.PI/4,t=this.effectAge;e.getTransform().setLocalPosition(new vec3(s.hx+Math.cos(a)*t*9,2+t*12-t*t*28,s.hz+Math.sin(a)*t*9));e.getTransform().setLocalRotation(quat.fromEulerAngles(t*5,i,t*4));}}
 }
}
