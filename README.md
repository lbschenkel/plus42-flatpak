# Plus42 (Flatpak)

This is a Flatpak package for Thomas Okken's most excellent
[Plus42](https://thomasokken.com/plus42/)
— an enhanced HP-42S calculator simulator.

## Installation

Pick one the following, from most recommended to least:

1. Add [my Flatpak repository](https://lbschenkel.github.io/flatpaks/).
   That will make Plus42 and my other Flatpaks available,
   and you will get updates.

2. Download and open the [.flatpakref](https://raw.githubusercontent.com/lbschenkel/plus42-flatpak/refs/heads/main/com.thomasokken.plus42.flatpakref).
   It will download from my repo and you will get updates, but only for
   this particular Flatpak.

3. Download the individual Flatpak bundle from
   [releases](https://github.com/lbschenkel/plus42-flatpak/releases).
   You will not get any updates and need to install any new versions manually.

### Permissions

This Flatpak requests the following permissions:
- network: disabled
- filesystem: only `$HOME/Downloads`

To give access to the whole `$HOME` directory you can use
[Flatseal](https://github.com/tchx84/Flatseal) or:
```
flatpak override --user --filesystem=home com.thomasokken.plus42
```

## Building it yourself

Use the `build.sh` script or something like:
```
flatpak run org.flatpak.Builder \
  --arch=x86_64 \
  --install --install-deps-from=flathub \
  --force-clean build \
  com.thomasokken.plus42

flatpak run com.thomasokken.plus42
```

## FAQ

**Why is this not in Flathub?**

Unfortunately a submission to Flathub
[would not be approved](https://github.com/flathub/flathub/pull/5768/)
due to upstream packaging practices not being acceptable to Flathub.
If the situation changes in the future I will try again.
