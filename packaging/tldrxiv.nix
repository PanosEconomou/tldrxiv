{ lib, python3Packages, fetchPypi }:

python3Packages.buildPythonApplication rec {
  pname = "tldrxiv";
  version = "0.1.1";
  pyproject = true;

  src = fetchPypi {
    inherit pname version;
    hash = "sha256-fmjAtQZVaQ6GJLbKnlcMKFiwnu15c0xkjVNYaga3iGQ=";
  };

  build-system = [ python3Packages.hatchling ];
  dependencies = [ ];

  pythonImportsCheck = [ "tldrxiv" ];
  doCheck = false;

  meta = {
    description = "Generate digests for daily arXiv feeds";
    homepage = "https://github.com/PanosEconomou/tldrxiv";
    license = lib.licenses.mit;
    mainProgram = "tldrxiv";
    platforms = lib.platforms.all;
  };
}
