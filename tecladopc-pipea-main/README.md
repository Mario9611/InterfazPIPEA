# Tecladopc-pipea

Este dispositivo permite al usuario proponer acciones por medio de un teclado QWERTY que se ponen en el aire por medio de un ESP32. La interfaz entre el teclado y el ESP32 es un shield Host USB.

Teclado QWERTY --> Mini USB host shield --> ESP-WROOM-32 (ESP32)

El teclado QWERTYT se conecta al USB host shield por medio de un puerto USB 2.0. Luego, el USB host shield se conecta al ESP32. Puede utilizar el siguiente diagrama de conexión como referencia.

Diagrama de conexión:

| USB host | ESP32  |
|----------|--------|
| Vcc      | 3.3V   |
| GND      | GND    |
| SS       | GPIO 5 (D5) |
| MOSI     | GPIO23 (D23) |
| MISO     | GPIO19 (D19) |
| CLK      | GPIO18 (D18) |
| INT      | GPIO17 (TX2) |
| VBUS     | Vin          |
| MAX_RST  | 3.3V         |

Se escogió el Mini USB host shield porque trabaja a 3.3 VDC, igual que el ESP32. Sin embargo, algunos dispositivos USB requieren que se conecten al shield requieren que el USB host los alimente a una tensión de 5 VDC. Para lograr esto, es necesario hacer una intervención en la placa del Mini USB host shield, cortando la pista que conecta el pin VBUS con el resistor de 2.2 Kohm.

## Funcionamiento

Este controlador recibe las señales que produce el usuario que propone las acciones por medio del teclado QWERTY. El usuario debe haber definido previamente cuales son las acciones que se quieren utilizar para poder mapearlas a teclas específicas en el teclado que sean representativas a las acciones. Por ejemplo, si una acción está relacionada con que un personaje se pone triste, se puede utilizar la tecla T.

El ESP32 recibe la señal de la tecla que fue presionada y la compara con una lista acciones que fue definida previamente. A partir de esto el ESP32 crea el mensaje que será enviado para que los personajes puedan actuar. Según la especificación de PIPEA, se utiliza el protocolo MQTT para transportar estos mensajes. 

MQTT es un protocolo publicador-suscriptor. Hay dispositivos que generan datos y hay dispositivos que están interesados en esos datos. Para hacerla asignación entre los datos generados y quienes tienen interés en esos, MQTT utiliza tópicos. Para PIPEA los tópicos siguen la forma. pipea/acción/actor. PIPEA propone que en la carga útil del mensaje esté el identificador de la acción, que puede ser un int. Además, propone que se pueden enviar otros datos relacionados a la acción propuesta, por ejemplo, parámetros relacionados a la acción. Para implementar esto, PIPEA propone utilizar formato json (no se ha implementado aún).


{"Triste": 25, "intensidad": 60, "color": 10}

## Conexión

El dispositivo ESP32 debe conectarse al broker local diseñado para PIPEA. Para conectarse a este broker, el primer paso es conectarse a la red inalámbrica con los siguientes datos: 

SSID: PIPEA
contraseña: "electrizartepipea" 

El broker es un servicio en un raspberry pi 3 model B. Para acceder al broker, se deben utilizar la siguiente información

dirección IP: 192.168.0.100 (eliminar cuando esté funcionando correctamente el dominio)
dominio: mqttbroker.pipea.eie.ucr.ac.cr  
puerto: 1883 


## Getting started

To make it easy for you to get started with GitLab, here's a list of recommended next steps.

Already a pro? Just edit this README.md and make it your own. Want to make it easy? [Use the template at the bottom](#editing-this-readme)!

## Add your files

- [ ] [Create](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#create-a-file) or [upload](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#upload-a-file) files
- [ ] [Add files using the command line](https://docs.gitlab.com/ee/gitlab-basics/add-file.html#add-a-file-using-the-command-line) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin https://git.ucr.ac.cr/electrizarte/tecladopc-pipea.git
git branch -M main
git push -uf origin main
```

## Integrate with your tools

- [ ] [Set up project integrations](https://git.ucr.ac.cr/electrizarte/tecladopc-pipea/-/settings/integrations)

## Collaborate with your team

- [ ] [Invite team members and collaborators](https://docs.gitlab.com/ee/user/project/members/)
- [ ] [Create a new merge request](https://docs.gitlab.com/ee/user/project/merge_requests/creating_merge_requests.html)
- [ ] [Automatically close issues from merge requests](https://docs.gitlab.com/ee/user/project/issues/managing_issues.html#closing-issues-automatically)
- [ ] [Enable merge request approvals](https://docs.gitlab.com/ee/user/project/merge_requests/approvals/)
- [ ] [Set auto-merge](https://docs.gitlab.com/ee/user/project/merge_requests/merge_when_pipeline_succeeds.html)

## Test and Deploy

Use the built-in continuous integration in GitLab.

- [ ] [Get started with GitLab CI/CD](https://docs.gitlab.com/ee/ci/quick_start/index.html)
- [ ] [Analyze your code for known vulnerabilities with Static Application Security Testing (SAST)](https://docs.gitlab.com/ee/user/application_security/sast/)
- [ ] [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/ee/topics/autodevops/requirements.html)
- [ ] [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/ee/user/clusters/agent/)
- [ ] [Set up protected environments](https://docs.gitlab.com/ee/ci/environments/protected_environments.html)

***

# Editing this README

When you're ready to make this README your own, just edit this file and use the handy template below (or feel free to structure it however you want - this is just a starting point!). Thanks to [makeareadme.com](https://www.makeareadme.com/) for this template.

## Suggestions for a good README

Every project is different, so consider which of these sections apply to yours. The sections used in the template are suggestions for most open source projects. Also keep in mind that while a README can be too long and detailed, too long is better than too short. If you think your README is too long, consider utilizing another form of documentation rather than cutting out information.

## Name
Choose a self-explaining name for your project.

## Description
Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Badges
On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage
Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Authors and acknowledgment
Show your appreciation to those who have contributed to the project.

## License
For open source projects, say how it is licensed.

## Project status
If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.
