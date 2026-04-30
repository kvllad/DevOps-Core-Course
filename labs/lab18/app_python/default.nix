{ pkgs ? import <nixpkgs> {} }:

let
  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    fastapi
    uvicorn
    httpx
    prometheus-client
  ]);
in
pkgs.stdenvNoCC.mkDerivation {
  pname = "devops-info-service";
  version = "1.0.0";

  src = pkgs.lib.cleanSource ./.;
  nativeBuildInputs = [ pkgs.makeWrapper ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/bin $out/app
    cp app.py $out/app/app.py
    cp requirements.txt $out/app/requirements.txt

    makeWrapper ${pythonEnv}/bin/python $out/bin/devops-info-service \
      --add-flags "$out/app/app.py"

    runHook postInstall
  '';

  meta = with pkgs.lib; {
    description = "Reproducible build of the DevOps Info Service";
    license = licenses.mit;
    mainProgram = "devops-info-service";
    platforms = platforms.unix;
  };
}
