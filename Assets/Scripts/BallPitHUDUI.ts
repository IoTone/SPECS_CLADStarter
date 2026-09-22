/** Passive UIKit game HUD: displays game state and emits restart. */
import {BackPlate} from 'SpectaclesUIKit.lspkg/Scripts/BackPlate';
import {FlexLayout} from 'SpectaclesUIKit.lspkg/Scripts/Components/Layout2D/Flex/FlexLayout';
import {FlexItem} from 'SpectaclesUIKit.lspkg/Scripts/Components/Layout2D/Flex/FlexItem';
import {FlexAlign,FlexDirection,FlexJustify} from 'SpectaclesUIKit.lspkg/Scripts/Components/Layout2D/Flex/FlexTypes';
import {Button} from 'SpectaclesUIKit.lspkg/Scripts/Components/Button/Button';
import {ElementContent} from 'SpectaclesUIKit.lspkg/Scripts/Components/Content/ElementContent';
import Event from 'SpectaclesInteractionKit.lspkg/Utils/Event';
const REPLAY=requireAsset('../Icons/replay.png') as Texture;
const SCALE={Title1:{size:105,weight:700},HeadlineXL:{size:62,weight:700},Body:{size:39,weight:500},Button:{size:39,weight:500}};
function applyTextRole(t:Text,role:keyof typeof SCALE){t.size=SCALE[role].size;(t as Text & {weight?:number}).weight=SCALE[role].weight;}
@component
export class BallPitHUDUI extends BaseScriptComponent {
 @input @hint('Game title') title:string='BALL OUT';
 @input @hint('Panel width in cm') width:number=44;
 @input @hint('Accent color') @widget(new ColorWidget()) accent:vec4=new vec4(0.3,1,0.82,1);
 public onRestart=new Event<void>();
 private score:Text;private status:Text;private clock:Text;
 onAwake(){this.sceneObject.createComponent('Component.Canvas');const plate=this.sceneObject.createComponent(BackPlate.getTypeName()) as BackPlate;plate.size=new vec2(this.width,22);
 const c=this.obj(this.sceneObject,'HUD content');c.getTransform().setLocalPosition(new vec3(0,0,0.65));const f=c.createComponent(FlexLayout.getTypeName()) as FlexLayout;
 f.onInitialized.add(()=>{f.width=this.width;f.height=22;f.direction=FlexDirection.Column;f.alignItems=FlexAlign.Center;f.justifyContent=FlexJustify.Center;f.rowGap=0.65;f.paddingTop=1;f.paddingBottom=1;
 this.row(c,3.7,o=>{const t=this.text(o,this.title,'Title1',3.7);t.textFill.color=this.accent;});
 this.row(c,3,o=>{this.score=this.text(o,'48 / 48 BALLS LEFT','HeadlineXL',3);});
 this.row(c,2,o=>{this.clock=this.text(o,'00:00.0  •  READY','Body',2);});
 this.row(c,3,o=>{this.status=this.text(o,'Push, scoop or pinch + throw\nClear every ball over the rim','Body',3);});
 this.row(c,4.3,o=>{const b=o.createComponent(Button.getTypeName()) as Button;b.onInitialized.add(()=>{b.size=new vec3(15,4.3,1);});const label=this.obj(o,'Restart label');label.getTransform().setLocalPosition(new vec3(0,0,0.15));const ec=label.createComponent(ElementContent.getTypeName()) as ElementContent;ec.text='RESTART';ec.textSize=SCALE.Button.size;ec.leadingIcon=REPLAY;ec.sizeOverride=new vec2(14,4);b.onTriggerUp.add(()=>this.onRestart.invoke());});
 });
 }
 public setProgress(left:number,total:number,time:number,won:boolean,started:boolean){if(!this.score)return;this.score.text=won?'POOL CLEARED!':left+' / '+total+' BALLS LEFT';const minutes=Math.floor(time/60),seconds=(time%60).toFixed(1);this.clock.text=minutes.toString().padStart(2,'0')+':'+seconds.padStart(4,'0')+(won?'  •  FINISHED':started?'  •  GO!':'  •  READY');this.status.text=won?'Nice work! Try for a faster time.':'Push, scoop or pinch + throw\nClear every ball over the rim';}
 private obj(p:SceneObject,n:string){const o=global.scene.createSceneObject(n);o.setParent(p);return o;}
 private row(p:SceneObject,h:number,build:(o:SceneObject)=>void){const o=this.obj(p,'HUD row'),i=o.createComponent(FlexItem.getTypeName()) as FlexItem;i.overrideWidth=this.width-4;i.overrideHeight=h;i.flexShrink=0;build(o);(p.getComponent(FlexLayout.getTypeName()) as FlexLayout).addItems([i]);}
 private text(o:SceneObject,s:string,role:keyof typeof SCALE,h:number){const t=o.createComponent('Component.Text') as Text;t.text=s;applyTextRole(t,role);t.depthTest=true;t.horizontalAlignment=HorizontalAlignment.Center;t.verticalAlignment=VerticalAlignment.Center;t.horizontalOverflow=HorizontalOverflow.Overflow;t.layoutRect=Rect.create(-(this.width-4)/2,(this.width-4)/2,-h/2,h/2);return t;}
}
