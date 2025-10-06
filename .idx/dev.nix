'
{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Kivy and KivyMD dependencies
    python310
    python310Packages.pip
    kivy
    gst_all_1.gstreamer
    gst_all_1.gst-plugins-base
    gst_all_1.gst-plugins-good
    gst_all_1.gst-plugins-bad
    gst_all_1.gst-plugins-ugly
    gst_all_1.gst-libav
    sdl2
    sdl2_image
    sdl2_mixer
    sdl2_ttf
    # Python libraries from requirements.txt
    (python310.withPackages (ps: (with ps; [
      pip
      wheel
    ]) ++ (with builtins; filter (p: p != null) (map (p: (
      let
        l = builtins.split "
" (builtins.readFile ./requirements.txt);
        p_ = builtins.elemAt (builtins.split "==" p) 0;
      in
      if p_ == "kivymd" then null else python310.pkgs.buildPythonPackage {
        name = p_;
        src = fetchPypi {
          pname = p_;
          version = builtins.elemAt (builtins.split "==" p) 1;
          sha256 = "0000000000000000000000000000000000000000000000000000"; # Placeholder, will be filled by Nix
        };
        doCheck = false;
        propagatedBuildInputs = with ps; [ ];
      }
    )) l))))
  ];

  shellHook = ''
    export KIVY_GL_BACKEND=sdl2
    export KIVY_GRAPHICS_BACKEND=sdl2
  '';
}
