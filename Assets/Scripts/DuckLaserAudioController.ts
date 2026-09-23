// DuckLaserAudioController — all Laser Duck audio in one place.
//
// Owns:    the looping 80s arcade chiptune bed and the SFX cues (laser pew, shield deflect,
//          player hit, duck squeak). It creates its own AudioComponents at runtime.
// Expects: the five AudioTrackAsset inputs, wired to Assets/GeneratedSFX/*.wav by the bootstrap.
// Must NOT: decide when cues fire. DuckLaserMain calls the play*() helpers.

@component
export class DuckLaserAudioController extends BaseScriptComponent {
  @ui.label('<span style="color: #60A5FA;">DuckLaserAudioController – music bed + SFX cues</span>')
  @ui.separator

  @ui.label('<span style="color: #60A5FA;">References</span>')
  @ui.group_start("References")
  @input
  @hint("Looping background music (80s arcade chiptune)")
  musicTrack!: AudioTrackAsset

  @input
  @hint("Played every time a duck eye fires a laser")
  laserShotSfx!: AudioTrackAsset

  @input
  @hint("Played when your shield deflects a laser")
  deflectSfx!: AudioTrackAsset

  @input
  @hint("Played when a laser hits you (game over)")
  hitSfx!: AudioTrackAsset

  @input
  @hint("Duck squeak, played when you step into the danger zone")
  squeakSfx!: AudioTrackAsset
  @ui.group_end

  @ui.separator
  @ui.label('<span style="color: #60A5FA;">Settings</span>')
  @ui.group_start("Settings")
  @input
  @hint("Background music volume (keep it under the SFX so cues stay readable)")
  @widget(new SliderWidget(0, 1, 0.05))
  musicVolume: number = 0.4

  @input
  @hint("Volume for all sound effects")
  @widget(new SliderWidget(0, 1, 0.05))
  sfxVolume: number = 0.9
  @ui.group_end

  private music: AudioComponent | null = null
  private laserVoices: AudioComponent[] = []
  private laserIdx = 0
  private deflect: AudioComponent | null = null
  private hit: AudioComponent | null = null
  private squeak: AudioComponent | null = null

  onAwake(): void {
    // Background bed: LowPower (latency-tolerant), loops forever.
    this.music = this.makeVoice("Music", this.musicTrack, this.musicVolume, false)
    if (this.music) this.music.play(-1)

    for (let i = 0; i < 3; i++) {
      const v = this.makeVoice(`LaserShot_${i}`, this.laserShotSfx, this.sfxVolume * 0.7, true)
      if (v) this.laserVoices.push(v)
    }
    this.deflect = this.makeVoice("Deflect", this.deflectSfx, this.sfxVolume, true)
    this.hit = this.makeVoice("Hit", this.hitSfx, this.sfxVolume, true)
    this.squeak = this.makeVoice("Squeak", this.squeakSfx, this.sfxVolume, true)
  }

  playLaser(): void {
    if (this.laserVoices.length === 0) return
    const v = this.laserVoices[this.laserIdx % this.laserVoices.length]
    this.laserIdx++
    v.stop(false)
    v.play(1)
  }

  playDeflect(): void { this.restart(this.deflect) }
  playHit(): void { this.restart(this.hit) }
  playSqueak(): void { this.restart(this.squeak) }

  private restart(a: AudioComponent | null): void {
    if (!a) return
    if (a.isPlaying()) a.stop(false)
    a.play(1)
  }

  private makeVoice(name: string, track: AudioTrackAsset, volume: number, lowLatency: boolean): AudioComponent | null {
    if (!track) {
      print(`[DuckLaserAudioController] WARN: ${name} track not wired`)
      return null
    }
    const so = global.scene.createSceneObject(name)
    so.setParent(this.getSceneObject())
    const a = so.createComponent("Component.AudioComponent") as AudioComponent
    a.audioTrack = track
    a.volume = volume
    // SFX tied to gameplay want LowLatency. The music bed stays on the Specs default, LowPower.
    a.playbackMode = lowLatency ? Audio.PlaybackMode.LowLatency : Audio.PlaybackMode.LowPower
    return a
  }
}
