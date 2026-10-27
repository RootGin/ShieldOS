{
  description = "shieldOS-eww development environment";

  inputs = {
    nixpkgs.url = "flake:nixpkgs";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      rajdhani = pkgs.stdenvNoCC.mkDerivation {
        pname = "rajdhani";
        version = "2.000";
        src = pkgs.fetchFromGitHub {
          owner = "itfoundry";
          repo = "rajdhani";
          rev = "v2.000";
          hash = "sha256-LA1YFa5J2jFLiPGrm7SbmLTfZk3amLyH2frTDNBj4BM=";
        };
        installPhase = "install -m 444 -Dt $out/share/fonts/opentype build/*.otf";
      };
      shieldFonts = pkgs.symlinkJoin {
        name = "shield-fonts";
        paths = [
          rajdhani
          pkgs.barlow
          pkgs.orbitron
          pkgs.nerd-fonts.shure-tech-mono
        ];
      };
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        packages = [
          pkgs.eww
          pkgs.dart-sass
          pkgs.sway
          pkgs.grim
          pkgs.imagemagick
          pkgs.fontconfig
          rajdhani
          pkgs.barlow
          pkgs.orbitron
          pkgs.nerd-fonts.shure-tech-mono
          (pkgs.python3.withPackages (ps: [ ps.jsonschema ]))
        ];
        SHIELD_FONTS = "${shieldFonts}";
      };
    };
}
