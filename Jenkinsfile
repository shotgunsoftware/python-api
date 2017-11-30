#!groovy
@Library("shared_libraries")
import shotgun.jenkins.Pipeline


properties([buildDiscarder(logRotator(daysToKeepStr:"31",numToKeepStr:"30"))])

def stages = [nosetests: [command: "nosetest -v"]]

parallel(
        py26: {new Pipeline(this, "python_api-26").build(stages)},
        py27: {new Pipeline(this, "python_api-27").build(stages)},
)

