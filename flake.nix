{
  description = "Generate digests for daily arXiv feeds";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in {
        packages.default = pkgs.python3Packages.buildPythonApplication {
          pname = "tldrxiv";
          version = builtins.head (builtins.match ''.*__version__ = "([^"]+)".*'' (builtins.readFile ./src/tldrxiv/__init__.py));
          pyproject = true;
          src = ./.;
          build-system = [ pkgs.python3Packages.hatchling ];
          pythonImportsCheck = [ "tldrxiv" ];
          meta.mainProgram = "tldrxiv";
        };

        devShells.default = pkgs.mkShell {
          packages = with pkgs.python3Packages; [ python hatchling build twine ];
        };
      }
    );
}
