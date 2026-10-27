{
  description = "shieldOS-eww development environment";

  inputs = {
    nixpkgs.url = "flake:nixpkgs";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        packages = [
          pkgs.eww
          pkgs.dart-sass
          pkgs.sway
          pkgs.grim
          pkgs.imagemagick
          (pkgs.python3.withPackages (ps: [ ps.jsonschema ]))
        ];
      };
    };
}
