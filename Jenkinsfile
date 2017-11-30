#!groovy
@Library("shared_libraries")
import shotgun.jenkins.Pipeline


properties([buildDiscarder(logRotator(daysToKeepStr:"31",numToKeepStr:"30"))])

def pipeline26 = new Pipeline(this, "python_api-26")
pipeline26.dockerBuildParameters = "-f Dockerfile.py26 ."
def pipeline27 = new Pipeline(this, "python_api-27")
pipeline27.dockerBuildParameters = "-f Dockerfile.py27 ."
def stages = [nosetests: [command: "nosetests -v"]]

parallel(
        py26: { pipeline26.build(stages) },
        py27: { pipeline27.build(stages) }
)
