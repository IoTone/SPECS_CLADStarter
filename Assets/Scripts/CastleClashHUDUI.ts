/** Passive UIKit controls; emits intent only, never owns game rules. */
import Event from 'SpectaclesInteractionKit.lspkg/Utils/Event';
import {BackPlate} from 'SpectaclesUIKit.lspkg/Scripts/BackPlate';
import {Button} from 'SpectaclesUIKit.lspkg/Scripts/Components/Button/Button';
import {Slider} from 'SpectaclesUIKit.lspkg/Scripts/Components/Slider/Slider';
import {ElementContent} from 'SpectaclesUIKit.lspkg/Scripts/Components/Content/ElementContent';
import {FlexLayout} from 'SpectaclesUIKit.lspkg/Scripts/Components/Layout2D/Flex/FlexLayout';
import {FlexItem} from 'SpectaclesUIKit.lspkg/Scripts/Components/Layout2D/Flex/FlexItem';
import {FlexAlign,FlexDirection,FlexJustify} from 'SpectaclesUIKit.lspkg/Scripts/Components/Layout2D/Flex/FlexTypes';
const TYPE_SCALE={Title:{size:62,weight:700},Body:{size:39,weight:500}};
@component
export class CastleClashHUDUI extends BaseScriptComponent {
 @input @hint('Width of the local control panel, cm') @widget(new SliderWidget(24,44,1)) width:number=32;
 onAction=new Event<string>(); onShield=new Event<number>(); private status:Text;private score:Text;private slider:Slider;private full:SceneObject;private compact:SceneObject;private compactScore:Text;private compactStatus:Text;
 private pendingStatus='Place the board, then Ready';private pendingScore='CASTLE CLASH';
 onAwake(){this.createEvent('OnStartEvent').bind(()=>this.build());}
 setStatus(value:string){this.pendingStatus=value;if(this.status)this.status.text=value;if(this.compactStatus)this.compactStatus.text=value;}
 setScore(value:string){this.pendingScore=value;if(this.score)this.score.text=value;if(this.compactScore)this.compactScore.text=value;}
 setCompact(value:boolean){if(this.full){this.full.enabled=!value;this.compact.enabled=value;}}
 private obj(parent:SceneObject,name:string,z=0){const o=global.scene.createSceneObject(name);o.setParent(parent);o.getTransform().setLocalPosition(new vec3(0,0,z));return o;}
 private child(parent:SceneObject,w:number,h:number){const o=this.obj(parent,'Item',0.03);const i=o.createComponent(FlexItem.getTypeName()) as FlexItem;i.overrideWidth=w;i.overrideHeight=h;i.flexShrink=0;(parent.getComponent(FlexLayout.getTypeName()) as FlexLayout).addItems([i]);return o;}
 private layout(parent:SceneObject,w:number,h:number,row=false){const o=this.obj(parent,'Layout',0.03);const f=o.createComponent(FlexLayout.getTypeName()) as FlexLayout;f.autoDiscoverItemsOnStart=false;f.onInitialized.add(()=>{f.width=w;f.height=h;f.direction=row?FlexDirection.Row:FlexDirection.Column;f.justifyContent=FlexJustify.Center;f.alignItems=FlexAlign.Center;f.rowGap=0.7;f.columnGap=0.6;});return o;}
 private text(parent:SceneObject,value:string,title=false){const t=this.obj(parent,'Label',0.15).createComponent('Component.Text') as Text;t.text=value;t.depthTest=true;const role=title?TYPE_SCALE.Title:TYPE_SCALE.Body;t.size=role.size;t.horizontalAlignment=HorizontalAlignment.Center;t.verticalAlignment=VerticalAlignment.Center;t.horizontalOverflow=HorizontalOverflow.Overflow;t.verticalOverflow=VerticalOverflow.Overflow;return t;}
 private button(row:SceneObject,label:string,action:string,w:number){const o=this.child(row,w,3.2);o.name=label;const b=o.createComponent(Button.getTypeName()) as Button;b.size=new vec3(w,3.2,1);const labelObject=this.obj(o,'Button label',0.15);const ec=labelObject.createComponent(ElementContent.getTypeName()) as ElementContent;ec.text=label;ec.textSize=TYPE_SCALE.Body.size;ec.sizeOverride=new vec2(w-0.5,2);b.onTriggerUp.add(()=>this.onAction.invoke(action));}
 private build(){this.sceneObject.createComponent('Component.Canvas');this.full=this.obj(this.sceneObject,'Setup controls');const plate=this.full.createComponent(BackPlate.getTypeName()) as BackPlate;plate.size=new vec2(this.width+2,26);
 const outer=this.layout(this.obj(this.full,'Content',0.7),this.width,25);this.score=this.text(this.child(outer,this.width,2.8),this.pendingScore,true);this.status=this.text(this.child(outer,this.width,3),this.pendingStatus);
 const placement=this.layout(this.child(outer,this.width,3.2),this.width,3.2,true);this.button(placement,'Place here','place',10);this.button(placement,'Lower','lower',7);this.button(placement,'Raise','raise',7);this.button(placement,'Turn','turn',6);
 const actions=this.layout(this.child(outer,this.width,3.2),this.width,3.2,true);this.button(actions,'Teal','teal',6);this.button(actions,'Amber','amber',7);this.button(actions,'Ready','ready',7);this.button(actions,'Rematch','rematch',9);
 const system=this.layout(this.child(outer,this.width,3.2),this.width,3.2,true);this.button(system,'Pause','pause',8);this.button(system,'Leave','leave',8);this.button(system,'Play CPU','cpu',12);
 const help=this.child(outer,this.width,2);this.text(help,'Pinch and slide to defend. Release to rest.');
 const control=this.child(outer,22,2.8);this.slider=control.createComponent(Slider.getTypeName()) as Slider;this.slider.size=new vec3(22,2.6,1);this.slider.currentValue=0.5;this.slider.onValueChange.add((v:number)=>this.onShield.invoke(v*54));this.slider.onKnobMoved.add((v:number)=>this.onShield.invoke(v*54));
 this.compact=this.obj(this.sceneObject,'Play controls');const smallPlate=this.compact.createComponent(BackPlate.getTypeName()) as BackPlate;smallPlate.size=new vec2(27,10);
 const small=this.layout(this.obj(this.compact,'Compact content',0.7),25,9);
 this.compactScore=this.text(this.child(small,25,1.5),this.pendingScore);this.compactScore.size=38;
 this.compactStatus=this.text(this.child(small,25,1.5),this.pendingStatus);this.compactStatus.size=27;
 const row=this.layout(this.child(small,25,3.2),25,3.2,true);
 const slide=this.child(row,17,2.8);slide.name='Shield control';const ss=slide.createComponent(Slider.getTypeName()) as Slider;ss.size=new vec3(17,2.6,1);ss.currentValue=0.5;ss.onValueChange.add((v:number)=>this.onShield.invoke(v*54));ss.onKnobMoved.add((v:number)=>this.onShield.invoke(v*54));this.button(row,'Pause','pause',6);
 this.compact.enabled=false;
 }
}
