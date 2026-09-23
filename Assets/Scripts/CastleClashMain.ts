/** Coordinates authored board, passive HUD, pure rules, and optional SyncKit authority. */
import {SessionController} from 'SpectaclesSyncKit.lspkg/Core/SessionController';
import {CastleClashHUDUI} from './CastleClashHUDUI';
import {CastleClashSimulation,DEFAULT_RULES,Snapshot,clamp} from './CastleClashSimulation';
import {CastleClashPresentation} from './CastleClashPresentation';
import {CastleClashSession,Packet} from './CastleClashSession';
@component
export class CastleClashMain extends BaseScriptComponent {
 @ui.label('Castle Clash — tabletop defense')
 @ui.group_start('References')
 @input @hint('Authored board root') board:SceneObject;
 @input @hint('Authored teal castle root') castleA:SceneObject;
 @input @hint('Authored amber castle root') castleB:SceneObject;
 @input @hint('Passive local controls') hud:CastleClashHUDUI;
 @input @hint('World tracked camera') camera:Camera;
 @input @hint('Vertex color geometry material') material:Material;
 @ui.group_end
 @ui.group_start('Game balance')
 @input @hint('Initial ball speed, cm/s') @widget(new SliderWidget(15,45,1)) ballSpeed:number=28;
 @input @hint('Ball speed cap, cm/s') @widget(new SliderWidget(40,90,1)) maxBallSpeed:number=62;
 @input @hint('Shared human and CPU shield speed cap, cm/s') @widget(new SliderWidget(20,65,1)) shieldSpeed:number=40;
 @input @hint('Shield width in cm') @widget(new SliderWidget(4,12,0.5)) shieldWidth:number=7;
 @input @hint('Seconds before symmetric wall removal') @widget(new SliderWidget(30,120,5)) suddenDeath:number=75;
 @input @hint('Initial and recovery countdown seconds') @widget(new SliderWidget(1,5,0.5)) countdown:number=3;
 @input @hint('Round wins needed') @widget(new SliderWidget(1,5,1)) roundsToWin:number=2;
 @ui.group_end
 @ui.group_start('Average CPU')
 @input @hint('Seconds between observations, not every-frame perfect tracking') @widget(new SliderWidget(0.15,0.8,0.01)) cpuReaction:number=0.35;
 @input @hint('Random timing variation either side of reaction interval') @widget(new SliderWidget(0,0.2,0.01)) cpuReactionJitter:number=0.07;
 @input @hint('Bounded stable aiming error along the rail in cm') @widget(new SliderWidget(0,8,0.1)) cpuAimError:number=3.4;
 @input @hint('Chance to hesitate for an additional decision interval') @widget(new SliderWidget(0,0.4,0.01)) cpuLapseChance:number=0.12;
 @ui.group_end
 @ui.group_start('Presentation')
 @input @hint('Impact cue volume') @widget(new SliderWidget(0,1,0.05)) volume:number=0.3;
 @input @hint('Starting table distance in cm') @widget(new SliderWidget(45,130,1)) tableDistance:number=85;
 @input @hint('Table below seated eye position, cm') @widget(new SliderWidget(15,70,1)) tableDrop:number=40;
 @ui.group_end
 public simulation:CastleClashSimulation;private view:CastleClashPresentation;private session:CastleClashSession;
 private multiplayer=false;private accumulator=0;private netClock=0;private seats=['',''];private ready=[false,false];private localSide=0;private tracking=true;private heartbeat=[0,0];private tick=0;private pose:number[]=[];private remoteView:Snapshot;private initialized=false;private leftSession=false;private localShieldTarget=27;private localShieldVisual=27;private shieldDirty=false;private shieldSendClock=0;
 onAwake(){this.createEvent('OnStartEvent').bind(()=>this.start());this.createEvent('UpdateEvent').bind(()=>this.update());}
 private start(){if(!this.board||!this.hud||!this.material){console.error('Castle Clash references not wired');return;}
 this.simulation=new CastleClashSimulation({...DEFAULT_RULES,speed:this.ballSpeed,maxSpeed:this.maxBallSpeed,shieldSpeed:this.shieldSpeed,shieldWidth:this.shieldWidth,reaction:this.cpuReaction,reactionJitter:this.cpuReactionJitter,aimError:this.cpuAimError,lapseChance:this.cpuLapseChance,suddenDeath:this.suddenDeath,countdown:this.countdown,wins:this.roundsToWin});
 this.view=new CastleClashPresentation(this.board,this.castleA,this.castleB,this.material,this.shieldWidth,this.volume);
 this.multiplayer=SessionController.getInstance().getIsReady();
 if(this.multiplayer){this.localSide=-1;this.session=new CastleClashSession(this);this.session.onIntent=(id,data)=>this.intent(id,data);}
 this.hud.onAction.add(a=>this.action(a));this.hud.onShield.add(v=>{if(this.localSide===1)v=54-v;this.localShieldTarget=v;if(this.multiplayer)this.shieldDirty=true;else this.simulation.input(0,v);});
 const tracking=this.camera.getSceneObject().getComponent('Component.DeviceTracking') as DeviceTracking;tracking.trackingStatus.onStopped.add(()=>{this.tracking=false;this.action('pause');});tracking.trackingStatus.onStarted.add(()=>{this.tracking=true;});
 if(!this.multiplayer)this.place();this.initialized=true;console.log('Castle Clash ready: '+(this.multiplayer?'SyncKit':'offline CPU'));
 }
 private action(a:string){if(a==='leave'){if(this.multiplayer){this.session.leave();this.leftSession=true;}this.simulation.pause();this.hud.setCompact(false);this.hud.setStatus('Left match · Play CPU, or reopen Lens for friend');return;}if(a==='cpu'){if(this.leftSession||this.simulation.state.phase==='match'||this.simulation.state.phase==='practice'){if(this.multiplayer&&!this.leftSession)this.session.leave();this.multiplayer=false;this.leftSession=false;this.localSide=0;this.simulation.reset();this.place();}return;}if(this.leftSession)return;if(this.multiplayer){if(a==='place'||a==='lower'||a==='raise'||a==='turn'){if(!this.session.isOwner()){this.hud.setStatus('Only the host places the shared board');return;}this.adjust(a);return;}this.session.send({type:a});return;}
 if(a==='place'||a==='lower'||a==='raise'||a==='turn')this.adjust(a);
 if(a==='ready'&&this.tracking)this.simulation.ready();if(a==='pause')this.simulation.pause();if(a==='rematch'){this.simulation.reset();this.simulation.ready();}}
 private intent(id:string,d:any){if(!d||typeof d.type!=='string')return;const s=this.simulation.state;const side=this.seats.indexOf(id);
 if(d.type==='heartbeat'){if(side>=0){this.heartbeat[side]=getTime();if(d.tracking===false){this.simulation.pause();this.ready=[false,false];}}return;}
 if(d.type==='teal'||d.type==='amber'){if(s.phase!=='practice'&&s.phase!=='paused')return;const wanted=d.type==='teal'?0:1;if(!this.seats[wanted]||this.seats[wanted]===id){if(side>=0)this.seats[side]='';this.seats[wanted]=id;this.ready=[false,false];this.heartbeat[wanted]=getTime();}return;}
 if(side<0)return;
 if(d.type==='shield'&&typeof d.value==='number'&&isFinite(d.value))this.simulation.input(side,d.value);
 if(d.type==='pause'){this.simulation.pause();this.ready=[false,false];}
 if(d.type==='ready'){this.ready[side]=true;if(this.ready.every(Boolean)&&this.seats.every(Boolean)){this.simulation.ready();this.ready=[false,false];}}
 if(d.type==='rematch'&&s.phase==='match'){this.ready[side]=true;if(this.ready.every(Boolean)){this.simulation.reset();this.simulation.ready();this.ready=[false,false];}}
 }
 private adjust(a:string){if(this.simulation.state.phase!=='practice')return;if(a==='place')this.place();else{const t=this.board.getTransform();if(a==='turn')t.setLocalRotation(t.getLocalRotation().multiply(quat.fromEulerAngles(0,Math.PI/12,0)));else{const p=t.getLocalPosition();p.y+=a==='raise'?2:-2;t.setLocalPosition(p);}this.capturePose();}}
 private place(){const c=this.camera.getTransform(),head=c.getWorldPosition(),f=c.forward;f.y=0;const dir=f.normalize().uniformScale(-this.tableDistance);const t=this.board.getTransform();t.setWorldPosition(head.add(dir).add(new vec3(0,-this.tableDrop,0)));t.setWorldRotation(quat.lookAt(dir.uniformScale(-1),vec3.up()));this.capturePose();}
 private capturePose(){const t=this.board.getTransform(),p=t.getLocalPosition(),q=t.getLocalRotation();this.pose=[p.x,p.y,p.z,q.w,q.x,q.y,q.z];}
 private applyPose(p:number[]){if(!p||p.length!==7)return;this.board.getTransform().setLocalPosition(new vec3(p[0],p[1],p[2]));this.board.getTransform().setLocalRotation(new quat(p[3],p[4],p[5],p[6]));}
 private update(){if(!this.initialized)return;if(this.leftSession){this.hud.setStatus('Left match · Play CPU, or reopen Lens for friend');return;}const dt=Math.min(getDeltaTime(),0.1);this.shieldSendClock-=dt;if(this.multiplayer&&this.shieldDirty&&this.shieldSendClock<=0){this.shieldDirty=false;this.shieldSendClock=0.05;this.session.send({type:'shield',value:this.localShieldTarget});}let state=this.simulation.state;
 if(this.multiplayer){const net=this.session;if(!net.ready){this.hud.setStatus('Connecting shared game…');return;}
 this.netClock+=dt;if(this.netClock>=0.05){this.netClock=0;net.send({type:'heartbeat',tracking:this.tracking});}
 if(net.isOwner()){
 if(!this.pose.length)this.place();const users=net.users();for(let i=0;i<2;i++)if(this.seats[i]&&(!users.includes(this.seats[i])||getTime()-this.heartbeat[i]>1.5)){if(state.phase!=='practice'&&state.phase!=='match')this.simulation.pause();this.ready=[false,false];if(!users.includes(this.seats[i]))this.seats[i]='';}
 }else if(net.latest){const p=net.latest;this.seats=p.seats;this.ready=p.ready;this.applyPose(p.pose);state=p.state;if(getTime()-net.receivedAt>1.5){state={...state,phase:'paused'};}}
 this.localSide=this.seats.indexOf(net.localId);
 }
 if(!this.multiplayer||this.session.isOwner()){this.accumulator+=dt;while(this.accumulator>=1/120){this.simulation.step(1/120,!this.multiplayer);this.accumulator-=1/120;}state=this.simulation.state;
 if(this.multiplayer&&this.netClock===0)this.session.publish({state,seats:this.seats,ready:this.ready,pose:this.pose,tick:++this.tick});}
 let shown=state;if(this.multiplayer&&!this.session.isOwner()){if(!this.remoteView||this.remoteView.phase!==state.phase)this.remoteView={...state,shields:state.shields.slice()};const f=Math.min(1,dt*18);this.remoteView.x+=(state.x-this.remoteView.x)*f;this.remoteView.z+=(state.z-this.remoteView.z)*f;shown={...state,x:this.remoteView.x,z:this.remoteView.z,shields:state.shields.slice()};if(this.localSide>=0){this.localShieldVisual+=clamp(this.localShieldTarget-this.localShieldVisual,-this.shieldSpeed*dt,this.shieldSpeed*dt);shown.shields[this.localSide]=this.localShieldVisual;}if(this.session.ownerLost)shown.phase='paused';}
 this.view.render(shown,dt);this.hud.setCompact(shown.phase==='playing'||shown.phase==='countdown'||shown.phase==='round');this.positionHUD();const mode=this.multiplayer?'FRIEND':'CPU · AVERAGE';this.hud.setScore('TEAL '+state.scores[0]+'  —  '+state.scores[1]+' AMBER');
 let status=mode+' · '+(this.localSide===1?'You are amber':'You are teal');
 if(this.multiplayer&&this.localSide<0)status='Choose the castle nearest your seat';
 else if(state.phase==='practice')status='Align center marker · practice · Ready';
 else if(state.phase==='countdown')status='Get ready · '+Math.ceil(state.clock);
 else if(state.phase==='paused')status='Paused · restore tracking / partner · Ready';
 else if(state.phase==='round'||state.phase==='match')status=(state.winner===0?'Teal':'Amber')+' wins '+(state.phase==='match'?'the match! Rematch?':'the round!');
 else if(state.elapsed>=this.suddenDeath)status='SUDDEN DEATH · walls falling';
 this.hud.setStatus(status);
 }
 private positionHUD(){const side=this.localSide===1?1:0;const bt=this.board.getTransform();const world=bt.getWorldTransform().multiplyPoint(new vec3(0,25,side===0?-34:34));const t=this.hud.getTransform();t.setWorldPosition(world);t.setWorldRotation(quat.lookAt(this.camera.getTransform().getWorldPosition().sub(world),vec3.up()));}
}
