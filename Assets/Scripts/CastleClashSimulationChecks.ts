import { CastleClashSimulation, DEFAULT_RULES } from './CastleClashSimulation';

/** Deterministic rules checks; invoke explicitly during development, never per frame. */
export function runCastleClashSimulationChecks(): string[] {
    const passed: string[] = [];
    function check(name: string, test: () => void): void {
        try { test(); passed.push('PASS ' + name); }
        catch (error) { throw new Error('FAIL ' + name + ': ' + error); }
    }
    function expect(value: boolean, message: string): void {
        if (!value) { throw new Error(message); }
    }
    function make(): CastleClashSimulation {
        let seed = 1729;
        return new CastleClashSimulation({...DEFAULT_RULES}, () => {
            seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
            return seed / 4294967296;
        });
    }
    check('fast ball damages wall once and reflects', () => {
        const game = make(); const s = game.state;
        s.phase = 'playing'; s.x = 1.5; s.z = 14; s.vx = 0; s.vz = 600;
        s.shields[0] = s.targets[0] = 0;
        game.step(0.02, false);
        expect(s.walls[4] === 1, 'expected one damage to front wall');
        expect(s.vz < 0 && s.z < 18, 'ball tunneled through wall');
    });
    check('crown scores exactly once and next round restores walls', () => {
        const game = make(); const s = game.state;
        s.phase = 'playing'; s.walls.fill(0); s.x = 0; s.z = 20; s.vx = 0; s.vz = 28;
        game.step(0.2, false);
        expect(s.scores[1] === 1 && String(s.phase) === 'round', 'missing crown victory');
        game.step(0.2, false);
        expect(s.scores[1] === 1, 'duplicate score');
        for (let i = 0; i < 180; i++) { game.step(1 / 60, false); }
        expect(s.walls.every(hp => hp === 2), 'walls not restored');
        expect(s.scores[1] === 1, 'round reset lost match score');
    });
    check('match victory is terminal until reset', () => {
        const game = make(); const s = game.state;
        s.scores[1] = 1; s.phase = 'playing'; s.walls.fill(0);
        s.x = 0; s.z = 20; s.vx = 0; s.vz = 28;
        game.step(0.2, false);
        expect(String(s.phase) === 'match' && s.scores[1] === 2, 'match did not finish');
        for (let i = 0; i < 300; i++) { game.step(1 / 60, true); }
        expect(s.scores[1] === 2 && String(s.phase) === 'match', 'finished match changed');
        game.reset();
        expect(game.state.scores.every(score => score === 0), 'rematch retained score');
        expect(game.state.walls.every(hp => hp === 2), 'rematch retained damage');
    });
    check('pause freezes play and recovery preserves the rally', () => {
        const game = make(); const s = game.state;
        s.phase = 'playing'; s.x = 3; s.z = 2; s.vx = 8; s.vz = 20; s.elapsed = 12;
        game.pause(); game.step(10, true);
        expect(s.x === 3 && s.z === 2 && s.elapsed === 12, 'pause advanced play');
        game.ready();
        for (let i = 0; i < 1000 && String(s.phase) !== 'playing'; i++) { game.step(1 / 60, false); }
        expect(String(s.phase) === 'playing', 'did not resume');
        expect(Math.abs(s.x - 3) < 0.5 && Math.abs(s.z - 2) < 0.5, 'resume replaced rally with new serve');
        expect(s.vx === 8 && s.vz === 20, 'resume changed ball velocity');
    });
    check('sudden death removes matching walls on both castles', () => {
        const game = make(); const s = game.state;
        s.phase = 'playing'; s.elapsed = game.rules.suddenDeath;
        game.step(1 / 60, false);
        expect(s.walls.some(hp => hp === 0), 'sudden death did not open walls');
        for (let i = 0; i < 12; i++) { expect(s.walls[i] === s.walls[12 + i], 'asymmetric sudden death'); }
    });
    check('CPU reacts after a delay and obeys shield speed limits', () => {
        const game = make(); const s = game.state;
        s.phase = 'playing'; s.x = 10; s.z = 0; s.vx = 0; s.vz = -28;
        game.step(0.1, true);
        expect(s.shields[1] === 27, 'CPU reacted immediately');
        let moved = false;
        for (let i = 0; i < 120; i++) {
            const before = s.shields[1]; game.step(1 / 60, true);
            expect(Math.abs(s.shields[1] - before) <= game.rules.shieldSpeed / 60 + 0.00001, 'CPU teleported');
            moved = moved || Math.abs(s.shields[1] - before) > 0.001;
        }
        expect(moved, 'CPU never moved');
    });
    check('seeded rallies stay finite and within the arena', () => {
        const game = make(); game.ready();
        for (let i = 0; i < 18000; i++) {
            if (game.state.phase === 'match') { game.reset(); game.ready(); }
            game.input(0, 27 + 27 * Math.sin(i * 0.017)); game.step(1 / 120, true);
            const s = game.state;
            expect([s.x, s.z, s.vx, s.vz].every(Number.isFinite), 'nonfinite ball state');
            expect(Math.abs(s.x) <= 20 && Math.abs(s.z) <= 30, 'ball escaped arena');
            expect(s.walls.every(hp => hp >= 0 && hp <= 2), 'invalid wall health');
            expect(s.shields.every(p => p >= 0 && p <= 54), 'shield escaped rail');
        }
    });
    return passed;
}
