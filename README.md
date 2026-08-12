# Dehype AI

Most claims about AI agent capabilities - autonomous hacking, lateral movement, vulnerability discovery - come with little to no reproducible evidence or misterious blog posts full of marketing buzzwords.

Dehype AI is a controlled lab that produces that evidence. Each experiment gives an LLM agent a shell and a goal inside an isolated VM network, then logs every command, every reasoning step, and every outcome.

The questions we test:

- Given a goal and shell access, does the agent discover resources it was   never told about?
- Will it exploit vulnerabilities to complete its task? How far does it go?
- Does its behavior change across models, prompts, or constraints?


## Architecture

```text
                         Windows Host
                  Python / AI Controller
                           |
                           | SSH: vm_shell
                           v
                    192.168.56.10
                           |
             VirtualBox Host-Only Network
                    192.168.56.0/24
                    /              \
                   v                v
        +------------------+   +------------------+
        | lab-agent        |   | lab-target       |
        | Ubuntu Server    |   | Ubuntu minimal   |
        | 192.168.56.10    |   | 192.168.56.20    |
        | user: agent      |   | test services /  |
        | no sudo          |   | target machine   |
        +------------------+   +------------------+
```

The host can administer both VMs over SSH, but the AI tool connects directly only to `lab-agent`.

### Network

| Machine | Host-Only IP | Role |
|---|---|---|
| Windows host | `192.168.56.1` | controller / administration |
| `lab-agent` | `192.168.56.10` | AI shell environment |
| `lab-target` | `192.168.56.20` | internal target / simulated services |

Each VM uses:

```text
Adapter 1: NAT
Adapter 2: Host-Only Adapter
```

NAT is useful for installation and updates. For experiments that are supposed to have **no Internet access**, disable Adapter 1 before the run.

Both VMs must use the same VirtualBox Host-Only network.

---

## Requirements

- Windows 10/11
- Oracle VirtualBox
- Ubuntu Server 24.04 LTS ISO
- Python 3
- Git
- OpenSSH Client
- OpenRouter API key as LLM provider

Suggested VM sizes:

```text
lab-agent:  2 vCPU, 2-4 GB RAM, 20-25 GB disk
lab-target: 1 vCPU, 1-2 GB RAM, 5-10 GB disk
```

## 1. Create the VMs

### VM 1 — `lab-agent`

Install Ubuntu Server with:

```text
Hostname: lab-agent
Host-Only IP: 192.168.56.10/24
SSH user used by the AI: agent
```

Install SSH if necessary:

```bash
sudo apt update
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
```

Create the dedicated AI user:

```bash
sudo adduser agent
id agent
```

`agent` must **not** belong to the `sudo` group. Administrative work should use a separate account.

### VM 2 — `lab-target`

Install a second, minimal Ubuntu Server VM with:

```text
Hostname: lab-target
Host-Only IP: 192.168.56.20/24
```

During installation select **Install OpenSSH server**, or install it afterward with the same commands used for `lab-agent`.

Keep `lab-target` minimal. It should contain only intentionally configured test services and synthetic/test data.

---

## 2. Configure the Host-Only addresses

Check the interface names on each VM:

```bash
ip -br addr
```

The Host-Only interface is normally `enp0s8`.

Create `/etc/netplan/60-lab-hostonly.yaml` on each VM:

```yaml
network:
  version: 2
  ethernets:
    enp0s8:
      dhcp4: false
      dhcp6: false
      addresses:
        - <HOST_ONLY_IP>/24
      optional: true
```

Use:

```text
lab-agent  -> 192.168.56.10
lab-target -> 192.168.56.20
```

Apply the configuration:

```bash
sudo chmod 600 /etc/netplan/60-lab-hostonly.yaml
sudo netplan generate
sudo netplan apply

ip -br addr
ip route
```

---

## 3. SSH access

Generate a dedicated key on Windows:

```powershell
ssh-keygen -t ed25519 -f $HOME\.ssh\dehype_lab
```

Install `dehype_lab.pub` in `~/.ssh/authorized_keys` for the appropriate user on both VMs.

Test `lab-agent`:

```powershell
ssh -i $HOME\.ssh\dehype_lab agent@192.168.56.10
```

Test `lab-target` with the administrator account created during installation:

```powershell
ssh -i $HOME\.ssh\dehype_lab <TARGET_ADMIN>@192.168.56.20
```


---

## 4. Environment configuration

Create `.env`:

```dotenv
LLM_API_KEY=<YOUR_API_KEY>

LAB_VM_HOST=192.168.56.10
LAB_VM_USER=agent
LAB_VM_SSH_KEY=C:/Users/<WINDOWS_USER>/.ssh/dehype_lab

LAB_MODEL=<MODEL_NAME>
```

Only `lab-agent` is configured as a tool endpoint. `lab-target` is a machine inside the lab network, not a second direct shell tool.

---

## 5. Project structure

```text
.
├── src/
│   └── dehype/
│       ├── agent.py         # controller + LLM runner
│       ├── context.py
│       └── vm_shell.py      # SSH tool exposed to the agent
├── scenarios/
│   └── 01-sqli-flask/       # each scenario is a self-contained folder
│       ├── README.md
│       ├── scenario.yaml
│       ├── prompt.txt
│       ├── target/
│       └── breadcrumbs/
├── logs/
├── .env
└── README.md
```

`vm_shell.py` provides:

```text
AI Agent -> vm_shell(command) -> SSH -> agent@192.168.56.10 -> lab-agent
```

The second VM is intentionally not hardcoded into the tool layer.

Scenarios are selected via the `LAB_SCENARIO` environment variable (defaults to `01-sqli-flask`). See [scenarios/README.md](scenarios/README.md) for the full list and conventions.


## 6. Run

To start the controller:

```powershell
.\.venv\Scripts\activate
python -m src.dehype.agent
```

The run should record the observable trail in the `logs` folder: tool calls, executed commands, command outputs/errors, and the final answer.
