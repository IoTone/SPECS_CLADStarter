// DuckLaserHudUI — passive HUD view for the Laser Duck game (generated per /specs-build-ui).
//
// Owns:    the HUD panel (BackPlate + FlexLayout column): title, Time / Best readouts,
//          a status line, and one Start / Restart / Play Again button.
// Expects: nothing wired. Icons and ImageMaterial load via requireAsset. Tunables are in Settings.
// Must NOT: hold game state or make game decisions. DuckLaserMain pushes values in through
//          setTime / setBest / setStatus / showIdle / showPlaying / showGameOver and listens
//          to onPlayPressed.
// Length: ~310 lines because the UIKit composition helpers (flexRow / flexChild / addText /
//          addImage) live inline so the module is self-contained, per /specs-build-ui.

import {FlexLayout} from "SpectaclesUIKit.lspkg/Scripts/Components/Layout2D/Flex/FlexLayout"
import {FlexItem} from "SpectaclesUIKit.lspkg/Scripts/Components/Layout2D/Flex/FlexItem"
import {
  FlexAlign,
  FlexAlignSelf,
  FlexDirection,
  FlexJustify,
} from "SpectaclesUIKit.lspkg/Scripts/Components/Layout2D/Flex/FlexTypes"
import {BackPlate} from "SpectaclesUIKit.lspkg/Scripts/BackPlate"
import {Button} from "SpectaclesUIKit.lspkg/Scripts/Components/Button/Button"
import {ElementContent} from "SpectaclesUIKit.lspkg/Scripts/Components/Content/ElementContent"
import Event, {PublicApi} from "SpectaclesInteractionKit.lspkg/Utils/Event"

// ── Assets (fixed internal assets, not Inspector-swappable) ────────────────
const imageMaterial = requireAsset("../Materials/ImageMaterial.mat") as Material
const ICON_TIMER: Texture = requireAsset("../Icons/timer.png") as Texture
const ICON_TROPHY: Texture = requireAsset("../Icons/trophy.png") as Texture
const ICON_PLAY: Texture = requireAsset("../Icons/play_arrow.png") as Texture
const ICON_REPLAY: Texture = requireAsset("../Icons/replay.png") as Texture

// ── Typography (canonical type scale, see specs-build-ui patterns.md) ──────
const FONT_SIZE_SCALE = 1.0
type TextRole =
  | "Title1" | "Title2" | "HeadlineXL" | "Headline1" | "Headline2"
  | "Subheadline" | "Button" | "Callout" | "Body" | "Caption"
const TYPE_SCALE: Record<TextRole, {size: number; weight: number}> = {
  Title1: {size: 105, weight: 700}, Title2: {size: 93, weight: 700},
  HeadlineXL: {size: 62, weight: 700}, Headline1: {size: 54, weight: 700},
  Headline2: {size: 48, weight: 700}, Subheadline: {size: 41, weight: 700},
  Button: {size: 39, weight: 500}, Callout: {size: 39, weight: 700},
  Body: {size: 39, weight: 500}, Caption: {size: 38, weight: 500},
}
function roleSize(role: TextRole, distanceCm: number = 110): number {
  return TYPE_SCALE[role].size * FONT_SIZE_SCALE * (distanceCm / 110)
}
function applyTextRole(t: Text, role: TextRole, distanceCm: number = 110): void {
  t.size = roleSize(role, distanceCm)
  ;(t as Text & {weight?: number}).weight = TYPE_SCALE[role].weight
}

const LAYOUT_Z_LIFT = 0.02
const BUTTON_LABEL_Z = 0.08

@component
export class DuckLaserHudUI extends BaseScriptComponent {
  @ui.label('<span style="color: #60A5FA;">DuckLaserHudUI – survival timer HUD + play button</span>')
  @ui.separator

  @ui.label('<span style="color: #60A5FA;">Settings</span>')
  @ui.group_start("Settings")
  @input
  @hint("Title shown at the top of the HUD")
  titleText: string = "LASER DUCK"

  @input
  @hint("Panel width in cm. The height follows the content.")
  @widget(new SliderWidget(24, 60, 1))
  panelWidthCm: number = 36

  @input
  @hint("Distance (cm) the HUD is read from. Text scales from the 110 cm Specs type scale by distance / 110.")
  @widget(new SliderWidget(80, 250, 5))
  viewingDistanceCm: number = 160

  @input("vec4", "{1.0, 0.86, 0.1, 1.0}")
  @hint("Accent color for the title and the Time / Best numbers (8-bit yellow)")
  @widget(new ColorWidget())
  accentColor: vec4

  @input("vec4", "{1.0, 0.25, 0.2, 1.0}")
  @hint("Status line color while you are in the danger zone or were shot down")
  @widget(new ColorWidget())
  dangerColor: vec4
  @ui.group_end

  // ── UI → Main events ──
  private _onPlayPressed = new Event<void>()
  /** Fires when the user taps the Start / Restart / Play Again button. */
  get onPlayPressed(): PublicApi<void> {
    return this._onPlayPressed.publicApi()
  }

  private timeText: Text | null = null
  private bestText: Text | null = null
  private statusText: Text | null = null
  private playContent: ElementContent | null = null
  private pendingStatus: {msg: string; danger: boolean} | null = null

  onAwake(): void {
    this.buildPanel()
  }

  // ── Main → UI setters ──────────────────────────────────────────────────
  setTime(seconds: number): void {
    if (this.timeText) this.timeText.text = `Time ${this.fmt(seconds)}`
  }

  setBest(seconds: number): void {
    if (this.bestText) this.bestText.text = `Best ${this.fmt(seconds)}`
  }

  setStatus(msg: string, danger: boolean = false): void {
    if (!this.statusText) {
      this.pendingStatus = {msg, danger}
      return
    }
    this.statusText.text = msg
    this.statusText.textFill.color = danger ? this.dangerColor : new vec4(1, 1, 1, 0.85)
  }

  /** Before the first run: Start button. */
  showIdle(): void {
    this.setPlayButton("Start", ICON_PLAY)
    this.setStatus("Press Start, then step close to the duck")
  }

  /** During a run: the button restarts the run. */
  showPlaying(): void {
    this.setPlayButton("Restart", ICON_REPLAY)
  }

  /** Run ended: show the final time and a Play Again button. */
  showGameOver(finalSeconds: number, bestSeconds: number): void {
    this.setTime(finalSeconds)
    this.setBest(bestSeconds)
    this.setPlayButton("Play Again", ICON_REPLAY)
    this.setStatus(`SHOT DOWN! You lasted ${this.fmt(finalSeconds)}`, true)
  }

  // ── Build ──────────────────────────────────────────────────────────────
  private buildPanel(): void {
    const D = this.viewingDistanceCm
    const W = this.panelWidthCm
    const k = D / 110
    const PAD = 2.0 * k

    this.sceneObject.createComponent("Component.Canvas")
    const backPlate = this.sceneObject.createComponent(BackPlate.getTypeName()) as BackPlate

    const content = this.obj(this.sceneObject, "Content", new vec3(0, 0, 0.6))
    const flex = content.createComponent(FlexLayout.getTypeName()) as FlexLayout
    flex.autoDiscoverItemsOnStart = false // items are registered explicitly via addItems (in build order)
    flex.width = W
    flex.height = -1
    flex.direction = FlexDirection.Column
    flex.justifyContent = FlexJustify.Start
    flex.alignItems = FlexAlign.Center
    flex.rowGap = 1.2 * k
    flex.paddingTop = PAD
    flex.paddingBottom = PAD
    flex.paddingLeft = PAD
    flex.paddingRight = PAD
    flex.onLayoutComplete.add((r) => {
      backPlate.size = new vec2(r.containerWidth, r.containerHeight)
    })

    const innerW = W - PAD * 2

    // Title
    const title = this.addText(content, this.titleText, "HeadlineXL", innerW, 3.2 * k, this.accentColor)
    ;(title.getSceneObject().getComponent(FlexItem.getTypeName()) as FlexItem).alignSelf = FlexAlignSelf.Stretch

    // Stats row: [timer] Time 999.9s   [trophy] Best 999.9s
    const statW = 11 * 0.5 * k + 1.0 * k // "Time 999.9s" at Body
    const iconS = 2.4 * k
    const row = this.flexRow(content, innerW, 3.2 * k, 0.8 * k)
    this.flexChild(row, {w: iconS, h: iconS}, (c) => this.addImage(c, ICON_TIMER, iconS))
    this.flexChild(row, {w: statW, h: 3.0 * k}, (c) => {
      this.timeText = this.addText(c, "Time 0.0s", "Callout", statW, 3.0 * k, this.accentColor, false)
    })
    this.flexChild(row, {w: 1.5 * k, h: 1}, () => {}) // spacer
    this.flexChild(row, {w: iconS, h: iconS}, (c) => this.addImage(c, ICON_TROPHY, iconS))
    this.flexChild(row, {w: statW, h: 3.0 * k}, (c) => {
      this.bestText = this.addText(c, "Best 0.0s", "Callout", statW, 3.0 * k, this.accentColor, false)
    })

    // Status line (longest: "Step inside the danger zone to score!")
    const status = this.addText(content, "Press Start, then step close to the duck", "Body", innerW, 2.6 * k, new vec4(1, 1, 1, 0.85))
    ;(status.getSceneObject().getComponent(FlexItem.getTypeName()) as FlexItem).alignSelf = FlexAlignSelf.Stretch
    this.statusText = status
    if (this.pendingStatus) {
      this.setStatus(this.pendingStatus.msg, this.pendingStatus.danger)
      this.pendingStatus = null
    }

    // Play button: sole ElementContent face (icon + label), so no row-collapse risk
    const btnW = 16 * k
    const btnH = 3.6 * k
    const btnSO = this.obj(content, "PlayButton")
    this.liftInZ(btnSO, LAYOUT_Z_LIFT)
    const btn = btnSO.createComponent(Button.getTypeName()) as Button
    btn.size = new vec3(btnW, btnH, 1)
    const faceSO = this.obj(btnSO, "Face", new vec3(0, 0, BUTTON_LABEL_Z))
    const ec = faceSO.createComponent(ElementContent.getTypeName()) as ElementContent
    ec.leadingIcon = ICON_PLAY
    ec.leadingIconSize = 2.0 * k
    ec.text = "Start"
    ec.textSize = roleSize("Button", D)
    ec.contentAlignment = "center"
    ec.spacing = 0.6 * k
    ec.sizeOverride = new vec2(btnW - 0.5 * k, btnH)
    this.playContent = ec
    const btnItem = btnSO.createComponent(FlexItem.getTypeName()) as FlexItem
    btnItem.overrideWidth = btnW
    btnItem.overrideHeight = btnH
    ;(content.getComponent(FlexLayout.getTypeName()) as FlexLayout).addItems([btnItem])
    btn.onTriggerUp.add(() => this._onPlayPressed.invoke())
  }

  private setPlayButton(label: string, icon: Texture): void {
    if (!this.playContent) return
    this.playContent.text = label
    this.playContent.leadingIcon = icon
  }

  private fmt(seconds: number): string {
    return `${Math.max(0, seconds).toFixed(1)}s`
  }

  // ── Helpers ────────────────────────────────────────────────────────────
  private addText(parent: SceneObject, text: string, role: TextRole, widthCM: number, heightCM: number,
                  color: vec4, register: boolean = true): Text {
    const so = this.obj(parent, "Text")
    this.liftInZ(so, LAYOUT_Z_LIFT)
    const t = so.createComponent("Component.Text") as Text
    t.text = text
    t.depthTest = true
    applyTextRole(t, role, this.viewingDistanceCm)
    t.textFill.color = color
    t.horizontalAlignment = HorizontalAlignment.Center
    t.verticalAlignment = VerticalAlignment.Center
    t.horizontalOverflow = HorizontalOverflow.Overflow
    t.verticalOverflow = VerticalOverflow.Overflow
    t.layoutRect = Rect.create(-widthCM / 2, widthCM / 2, -heightCM / 2, heightCM / 2)
    if (register) {
      const item = so.createComponent(FlexItem.getTypeName()) as FlexItem
      item.overrideWidth = widthCM
      item.overrideHeight = heightCM
      const pf = parent.getComponent(FlexLayout.getTypeName()) as FlexLayout | null
      if (pf) pf.addItems([item])
    }
    return t
  }

  private addImage(parent: SceneObject, texture: Texture, sizeCM: number): void {
    const so = this.obj(parent, "Icon")
    const img = so.createComponent("Component.Image") as Image
    const mat = imageMaterial.clone()
    mat.mainPass.baseTex = texture
    mat.mainPass.depthTest = true
    mat.mainPass.depthWrite = false
    img.clearMaterials()
    img.addMaterial(mat)
    so.getTransform().setLocalScale(new vec3(sizeCM, sizeCM, 1))
  }

  private obj(parent: SceneObject, name: string, position?: vec3): SceneObject {
    const so = global.scene.createSceneObject(name)
    so.setParent(parent)
    if (position) so.getTransform().setLocalPosition(position)
    return so
  }

  private liftInZ(so: SceneObject, z: number): void {
    const tr = so.getTransform()
    const p = tr.getLocalPosition()
    tr.setLocalPosition(new vec3(p.x, p.y, p.z + z))
  }

  private flexRow(parent: SceneObject, width: number, height: number, gap: number): SceneObject {
    const container = this.obj(parent, "Row")
    this.liftInZ(container, LAYOUT_Z_LIFT)
    const fl = container.createComponent(FlexLayout.getTypeName()) as FlexLayout
    fl.autoDiscoverItemsOnStart = false
    const fi = container.createComponent(FlexItem.getTypeName()) as FlexItem
    fi.overrideWidth = width
    fi.overrideHeight = height
    fl.onInitialized.add(() => {
      fl.width = width
      fl.height = height
      fl.direction = FlexDirection.Row
      fl.columnGap = gap
      fl.justifyContent = FlexJustify.Center
      fl.alignItems = FlexAlign.Center
    })
    const pf = parent.getComponent(FlexLayout.getTypeName()) as FlexLayout | null
    if (pf) pf.addItems([fi])
    return container
  }

  private flexChild(parent: SceneObject, size: {w?: number; h?: number; grow?: number},
                    builder: (child: SceneObject) => void): SceneObject {
    const child = this.obj(parent, "Item")
    this.liftInZ(child, LAYOUT_Z_LIFT)
    const fi = child.createComponent(FlexItem.getTypeName()) as FlexItem
    if (size.w !== undefined && size.w > 0) fi.overrideWidth = size.w
    if (size.h !== undefined && size.h > 0) fi.overrideHeight = size.h
    fi.flexGrow = size.grow ?? 0
    fi.flexShrink = 0
    builder(child)
    const pf = parent.getComponent(FlexLayout.getTypeName()) as FlexLayout | null
    if (pf) pf.addItems([fi])
    return child
  }
}
