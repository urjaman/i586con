import setuptools

setuptools.setup(
    name="i586con-savestate",
    version="0.1",
    author="Urja Rannikko",
    author_email="urjaman@gmail.com",
    description="State saving / installation scripts for i586con",
    url="https://github.com/urjaman/i586con",
    packages=["hdslib"],
    scripts=[
        "bin/hdinstall",
        "bin/cd_save",
        "bin/hd_save",
        "bin/upgrade_hdi",
    ],
    license="MIT",
    python_requires=">=3.6",
)
