# Overview

A SPECS CLAD starter project for a quick onboarding into agentic workflows using Lens Studio 5.2x

## Setup

- Install Lens Studio 5.24.0 or greater (ensure you have a compatible version): https://ar.snap.com/download
- Install your favorite agent, cursor, codex, or claude : https://developers.specs.com/docs/clad/setup/setup-ai/claude-code-setup
- Install the plugins for CLAD
- Establish an MCP connection (make sure Lens Studio is running first, and is the right version)
- Enable auto-mode for this session (shift tab or enable through menus)
- Make sure you have a "specs" account and sign in via Lens Studio before kicking off a session.  A specs account is something additional to the snapchat account you need.

### Claude

There are a few gotchas that can come up.  Decide if you have GUI or CLI.  The main gotcha is what kind of account you have.  You need an account that lets you login with your username / password.  

### Cursor

No known gotchas.

### Codex

As with Claude, decide if you have installed via GUI or CLI.

## Code

You can create a SPECS project using the "Base Template" (https://developers.specs.com/docs/clad/setup/setup-lens-studio) or clone this repo using git: git clone.

### Prompts

This is the magic.  Think about what you want to build.  If you were giving instructions to someone, how would you constrain your request so it isn't open to too much interpretation.   This is key.  You want to avoid ambiguity.  Don't be too broad unless you are trying to be so.  

- For example: "Design a pool."  Could be interpreted in many ways.  Be more specific.  "Design a SPECS Lens with a pool full of plastic balls that are all interactable and show off real physics that you can interact with and push around with your hands.  Make it a game to empty the pool of all of the balls." Or "Design SPECS Lens with a pool table where hamsters play pool, and you bet on the winner of each round of pool played by hamsters (red team and blue team)". 

- The default example "Can you please build me a periodic table SPECS Lens showing the atomic structure of various elements?" 

- "Design a SPECS Lens that is a castle defense game played against someone sitting across the table from you.  It should be tabletop style.  Think Warlords atari game done in 3d."

