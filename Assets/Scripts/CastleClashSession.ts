/** SyncKit transport: authority owns snapshots/seats; peers submit authenticated intents. */
import {SessionController} from 'SpectaclesSyncKit.lspkg/Core/SessionController';
import {SyncEntity} from 'SpectaclesSyncKit.lspkg/Core/SyncEntity';
import {StorageProperty} from 'SpectaclesSyncKit.lspkg/Core/StorageProperty';
import {StoragePropertySet} from 'SpectaclesSyncKit.lspkg/Core/StoragePropertySet';
import {Snapshot} from './CastleClashSimulation';
export interface Packet {state:Snapshot;seats:string[];ready:boolean[];pose:number[];tick:number;}
export class CastleClashSession {
 entity:SyncEntity;ready=false;latest:Packet=null;receivedAt=0;localId='';ownerLost=false;
 private property=StorageProperty.manualString('castleState','');private beganOwner=false;private originalOwner='';
 private sc=SessionController.getInstance();
 onIntent:(id:string,data:any)=>void=()=>{};
 constructor(component:ScriptComponent){
 this.entity=new SyncEntity(component,new StoragePropertySet([this.property]),true,'Session');
 this.entity.onEventReceived.add('intent',m=>{if(this.isOwner())this.onIntent(m.senderConnectionId,m.data);});
 this.property.onAnyChange.add((v:string)=>{if(!v)return;try{this.latest=JSON.parse(v);this.receivedAt=getTime();}catch(e){console.warn('Castle snapshot rejected');}});
 this.entity.notifyOnReady(()=>{this.ready=true;this.localId=this.sc.getLocalConnectionId();this.beganOwner=this.entity.doIOwnStore();this.originalOwner=this.entity.ownerInfo?.connectionId||'';const v=this.property.currentOrPendingValue;if(v){this.latest=JSON.parse(v);this.receivedAt=getTime();}});
 this.entity.onOwnerUpdated.add(()=>{if(this.ready){const owner=this.entity.ownerInfo?.connectionId||'';if(!this.originalOwner&&owner)this.originalOwner=owner;else if(this.originalOwner!==owner)this.ownerLost=true;}});
 }
 leave(){this.ready=false;this.ownerLost=true;const active=this.sc.getSession();if(active)this.sc.connectedLensModuleToUse.leaveSession(active);}
 isOwner(){return this.ready&&this.entity.doIOwnStore()&&!this.ownerLost;}
 users(){return this.ready?this.sc.getUsers().map(u=>u.connectionId):[];}
 send(data:any){if(this.ready)this.entity.sendEvent('intent',data);}
 publish(packet:Packet){if(this.isOwner())this.property.setPendingValue(JSON.stringify(packet));}
}
