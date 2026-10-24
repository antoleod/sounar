# Example setups

Each file is a speaker map with the device names left empty. `sounar setup --example <name>`
fills in the positions and only asks which of your outputs is which. Positions are hours on a
clock face around your seat: 12 = straight ahead, 3 = your right, 6 = behind you, 9 = your left.

| Setup | Speakers | What the room presets do with it |
|---|---|---|
| [`stereo-pair`](stereo-pair.toml) | front left, front right | a clean left/right picture, vocal lift, bass lined up |
| [`pair-plus-rear`](pair-plus-rear.toml) | front pair + rear centre | the pair plays the song, the rear plays the room around it |
| [`quad`](quad.toml) | front pair + rear pair | the rear pair plays ambience, decorrelated left and right |
| [`left-centre-right`](left-centre-right.toml) | front pair + centre | vocals anchored in the centre, the pair carries the width |
| [`pair-with-sub`](pair-with-sub.toml) | front pair + subwoofer | the sub adds the low end under all presets |
| [`stereo-box-and-twin-right`](stereo-box-and-twin-right.toml) | stereo box front left, front right and rear right on one output | vocals anchored in the box you face, ambience from behind on the right (Sounar's first room) |

## Share yours

Got a room that works? Open a [Share your setup](https://github.com/zane8n/sounar/issues/new?template=share_setup.yml)
issue, or send a pull request with a new file here: copy the closest example, keep `node = ""`,
draw the room in the comment at the top, and add a line to the table above.
