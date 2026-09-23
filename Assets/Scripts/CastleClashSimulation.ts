/** Pure authoritative tabletop simulation. No scene, networking, or visual state. */
export type Phase = 'practice'|'countdown'|'playing'|'round'|'match'|'paused';
export interface Rules {speed:number;maxSpeed:number;shieldSpeed:number;shieldWidth:number;reaction:number;reactionJitter:number;aimError:number;lapseChance:number;suddenDeath:number;countdown:number;wins:number;}
export const DEFAULT_RULES:Rules={speed:28,maxSpeed:62,shieldSpeed:40,shieldWidth:7,reaction:0.35,reactionJitter:0.07,aimError:3.4,lapseChance:0.12,suddenDeath:75,countdown:3,wins:2};
export interface Rect {x:number;z:number;hx:number;hz:number;side:number;index:number;kind:string}
export interface Snapshot {phase:Phase;clock:number;elapsed:number;x:number;z:number;vx:number;vz:number;shields:number[];targets:number[];walls:number[];scores:number[];winner:number;event:number;hit:string;hx:number;hz:number;}
export const clamp=(x:number,a:number,b:number)=>Math.max(a,Math.min(b,x));
export function rail(s:number,side:number):{x:number;z:number;flank:boolean}{
 const k=side===0?1:-1; s=clamp(s,0,54);
 if(s<13)return{x:-14,z:k*(27-s),flank:true};
 if(s>41)return{x:14,z:k*(14+s-41),flank:true};
 return{x:s-27,z:k*14,flank:false};
}
export function walls():Rect[]{const out:Rect[]=[];for(let side=0;side<2;side++){const k=side===0?1:-1;
 for(let i=0;i<8;i++)out.push({x:-10.5+i*3,z:k*18,hx:1.48,hz:0.8,side,index:side*12+i,kind:'wall'});
 for(let f=0;f<2;f++)for(let j=0;j<2;j++)out.push({x:f===0?-12:12,z:k*(21+j*5),hx:0.8,hz:2.48,side,index:side*12+8+f*2+j,kind:'wall'});
 }return out;}
const WALLS=walls();
export class CastleClashSimulation {
 state:Snapshot; private cpuTimer=0;private cpuBias=0;private suddenIndex=0;private pausedPhase:Phase='playing';private pausedClock=0;private recovering=false;
 constructor(public rules:Rules={...DEFAULT_RULES},private random:()=>number=Math.random){this.reset();}
 reset(){this.state={phase:'practice',clock:0,elapsed:0,x:0,z:0,vx:0,vz:0,shields:[27,27],targets:[27,27],walls:Array(24).fill(2),scores:[0,0],winner:-1,event:0,hit:'',hx:0,hz:0};this.recovering=false;this.resetCpu();}
 resetCpu(){this.cpuTimer=this.rules.reaction;this.cpuBias=0;}
 ready(){if(this.state.phase==='practice'||this.state.phase==='paused'){this.recovering=this.state.phase==='paused';this.state.phase='countdown';this.state.clock=this.rules.countdown;}}
 pause(){if(this.state.phase!=='paused'&&this.state.phase!=='match'){if(!this.recovering){this.pausedPhase=this.state.phase;this.pausedClock=this.state.clock;}this.state.phase='paused';}}
 input(side:number,value:number){if(side===0||side===1)this.state.targets[side]=clamp(value,0,54);}
 private cue(kind:string){const s=this.state;s.event++;s.hit=kind;s.hx=s.x;s.hz=s.z;}
 private serve(){const a=(this.random()*0.9-0.45);const dir=this.state.scores.reduce((a,b)=>a+b,0)%2===0?-1:1;this.state.x=0;this.state.z=0;this.state.vx=Math.sin(a)*this.rules.speed;this.state.vz=dir*Math.cos(a)*this.rules.speed;this.state.phase='playing';}
 step(dt:number,cpu:boolean){const s=this.state;if(s.phase==='paused'||s.phase==='match')return;
 if(cpu)this.think(dt);
 for(let i=0;i<2;i++)s.shields[i]+=clamp(s.targets[i]-s.shields[i],-this.rules.shieldSpeed*dt,this.rules.shieldSpeed*dt);
 if(s.phase==='countdown'){s.clock-=dt;if(s.clock<=0){if(this.recovering){this.recovering=false;s.phase=this.pausedPhase;s.clock=this.pausedClock;}else this.serve();}return;}
 if(s.phase==='round'){s.clock-=dt;if(s.clock<=0){s.walls.fill(2);s.elapsed=0;this.suddenIndex=0;s.x=s.z=s.vx=s.vz=0;s.shields=[27,27];s.targets=[27,27];this.resetCpu();s.phase='countdown';s.clock=this.rules.countdown;}return;}
 if(s.phase!=='playing')return;
 s.elapsed+=dt;
 const wanted=Math.min(12,Math.max(0,Math.floor((s.elapsed-this.rules.suddenDeath)/2)+1));
 while(this.suddenIndex<wanted){const order=[3,4,2,5,1,6,0,7,8,10,9,11];s.walls[order[this.suddenIndex]]=0;s.walls[12+order[this.suddenIndex]]=0;this.suddenIndex++;this.cue('stone');}
 this.moveBall(dt);if(Math.abs(s.x)>18.8){s.x=clamp(s.x,-18.8,18.8);s.vx=-Math.sign(s.x)*Math.abs(s.vx);}if(Math.abs(s.z)>28.8){s.z=clamp(s.z,-28.8,28.8);s.vz=-Math.sign(s.z)*Math.abs(s.vz);}
 }
 private think(dt:number){this.cpuTimer-=dt;if(this.cpuTimer>0)return;
 this.cpuTimer=Math.max(0.12,this.rules.reaction+(this.random()*2-1)*this.rules.reactionJitter);
 if(this.random()<this.rules.lapseChance){this.cpuTimer+=this.rules.reaction;return;}
 this.cpuBias=(this.random()*2-1)*this.rules.aimError;
 const s=this.state;if(s.vz>=0||s.phase!=='playing'){this.input(1,27+this.cpuBias);return;}
 // One imperfect prediction per decision, held between decisions. Limited lookahead.
 const t=clamp((-14-s.z)/s.vz,0,1.2);let x=s.x+s.vx*t;
 while(x>18.5||x< -18.5){if(x>18.5)x=37-x;if(x< -18.5)x=-37-x;}
 let best=27,bestD=1e9;for(let p=0;p<=54;p++){const q=rail(p,1);const d=(q.x-x)**2+(q.z-(s.z+s.vz*t))**2;if(d<bestD){bestD=d;best=p;}}
 this.input(1,best+this.cpuBias);
 }
 private moveBall(dt:number){const s=this.state;let remaining=dt;
 for(let bounce=0;bounce<8&&remaining>0.000001;bounce++){
 const shapes:Rect[]=[{x:-20,z:0,hx:0.5,hz:31,side:-1,index:-1,kind:'rail'},{x:20,z:0,hx:0.5,hz:31,side:-1,index:-1,kind:'rail'},{x:0,z:-30,hx:20,hz:0.5,side:-1,index:-1,kind:'rail'},{x:0,z:30,hx:20,hz:0.5,side:-1,index:-1,kind:'rail'}];
 for(const w of WALLS)if(s.walls[w.index]>0)shapes.push(w);
 for(const side of [0,1])shapes.push({x:0,z:side===0?28.3:-28.3,hx:12.8,hz:0.8,side,index:-1,kind:'rear'});
 for(let side=0;side<2;side++){const p=rail(s.shields[side],side);shapes.push({x:p.x,z:p.z,hx:p.flank?0.55:this.rules.shieldWidth/2,hz:p.flank?this.rules.shieldWidth/2:0.55,side,index:-1,kind:'shield'});shapes.push({x:0,z:side===0?26:-26,hx:2.7,hz:2,side,index:-1,kind:'crown'});}
 let first=remaining+1,hit:Rect=null,nx=0,nz=0;
 for(const r of shapes){const c=this.sweep(r,remaining);if(c&&c.t<first){first=c.t;hit=r;nx=c.nx;nz=c.nz;}}
 if(!hit){s.x+=s.vx*remaining;s.z+=s.vz*remaining;break;}
 s.x+=s.vx*first;s.z+=s.vz*first;remaining-=first;
 if(hit.kind==='crown'){s.winner=1-hit.side;s.scores[s.winner]++;s.phase=s.scores[s.winner]>=this.rules.wins?'match':'round';s.clock=2.5;s.vx=s.vz=0;this.cue('win');return;}
 let speed=Math.sqrt(s.vx*s.vx+s.vz*s.vz);
 if(hit.kind==='shield'){
 if(nx)s.x=hit.x+nx*(hit.hx+0.702);else s.z=hit.z+nz*(hit.hz+0.702);
 const p=rail(s.shields[hit.side],hit.side);const offset=clamp((p.flank?s.z-p.z:s.x-p.x)/(this.rules.shieldWidth/2),-1,1);speed=Math.min(this.rules.maxSpeed,speed*1.05);
 if(!p.flank){const a=offset*0.95;s.vx=Math.sin(a)*speed;s.vz=(hit.side===0?-1:1)*Math.cos(a)*speed;}
 else{s.vx=(p.x<0?-1:1)*speed*0.75;s.vz=(hit.side===0?-1:1)*speed*Math.sqrt(1-0.75*0.75);}
 this.cue('shield');
 }else{if(nx)s.vx=-s.vx;if(nz)s.vz=-s.vz;if(hit.kind==='wall'){s.walls[hit.index]--;const f=Math.max(this.rules.speed,speed*0.92)/speed;s.vx*=f;s.vz*=f;this.cue('stone');}}
 const mag=Math.sqrt(s.vx*s.vx+s.vz*s.vz);s.x+=s.vx/mag*0.002;s.z+=s.vz/mag*0.002;
 }
 }
 private sweep(r:Rect,max:number):{t:number;nx:number;nz:number}|null{
 const s=this.state;const radius=0.7;
 if(r.kind==='shield'&&Math.abs(s.x-r.x)<r.hx+radius&&Math.abs(s.z-r.z)<r.hz+radius){const dx=(r.hx+radius)-Math.abs(s.x-r.x),dz=(r.hz+radius)-Math.abs(s.z-r.z);const nx=dx<dz?(s.x>=r.x?1:-1):0,nz=dx>=dz?(s.z>=r.z?1:-1):0;if(s.vx*nx+s.vz*nz<0){return{t:0,nx,nz};}}
 let enter=-Infinity,exit=Infinity,nx=0,nz=0;
 for(const axis of ['x','z']){const p=s[axis],v=axis==='x'?s.vx:s.vz,c=r[axis],h=(axis==='x'?r.hx:r.hz)+radius;
 if(Math.abs(v)<1e-9){if(p<c-h||p>c+h)return null;continue;}
 let a=(c-h-p)/v,b=(c+h-p)/v;const n=v>0?-1:1;if(a>b){const t=a;a=b;b=t;}if(a>enter){enter=a;nx=axis==='x'?n:0;nz=axis==='z'?n:0;}exit=Math.min(exit,b);}
 if(enter>exit||exit<0||enter< -0.00001||enter>max)return null;return{t:Math.max(0,enter),nx,nz};
 }
}
