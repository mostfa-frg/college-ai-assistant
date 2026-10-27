# Lecture 1: Course Introduction and Overview – Distributed Systems  

## 1. Lecture Overview  
- Introductory lecture for a course on Distributed Systems.  
- Covers basic definitions, real‑world examples (Google, Facebook, Cloud Computing), and why modern applications use multiple machines instead of a single powerful one.  

## 2. Learning Objectives  
| Objective | Description |
|---|---|
| Understand the definition of distributed systems | Recognize key components: nodes, processes, communication links, resource sharing. |
| Grasp fundamental concepts | Transparency, availability, scalability, consistency, fault tolerance. |
| Identify key design principles | Goals such as distribution transparency, openness, scalability and their trade‑offs. |
| Recognize core characteristics and challenges | Concurrent execution, lack of global clock, independent failures, heterogeneity, security, scalability, fault tolerance, quality of service. |
| Classify system types | Distributed Computing Systems (Clusters, Grids), Distributed Information Systems (Transaction processing, Enterprise systems), Distributed Pervasive Systems (IoT, Smart homes). |
| Explain architectural models | Client‑Server (two‑tier, three‑tier, N‑tier), Peer‑to‑Peer (centralized, decentralized, hybrid), SOA, Microservices. |
| Understand IPC mechanisms | Message passing, shared memory, sockets, ports, synchronous vs. asynchronous, RPC, RMI, middleware. |
| Explain synchronization techniques | Physical clocks, logical clocks (Lamport, vector), "happened‑before" relation. |
| Apply concurrency control | ACID properties, mutual exclusion, locks, two‑phase locking, deadlocks. |
| Study consensus protocols | Election algorithms (Bully, Ring), consensus (Paxos, Raft, Gossip). |

## 3. Detailed Study Notes  

### 3.1 Definition and Rationale  
- A *distributed system* consists of multiple autonomous computers (nodes) that communicate over a network to achieve a common goal.  
- Modern applications prefer this architecture because it offers **scalability** (handling more users), **fault tolerance** (continues operation despite failures), and **resource sharing** (leveraging multiple machines).  

### 3.2 Core Concepts  
| Concept | What it Means | Why It Matters |
|---|---|---|
| **Transparency** | Hiding the system’s complexity from users. | Improves usability. |
| **Scalability** | Ability to grow with added users or workload. | Ensures performance under load. |
| **Consistency** | All replicas show identical data. | Critical for correctness. |
| **Fault Tolerance** | System keeps working when parts fail. | Enhances reliability. |
| **Availability** | System always responds to requests. | Guarantees service uptime. |

### 3.3 System Components  
- **Nodes**: Independent machines or processes.  
- **Processes**: Programs running on nodes.  
- **Communication Links**: Physical or logical channels (TCP/UDP sockets).  
- **Resource Sharing**: File systems, databases, network bandwidth.  

### 3.4 Design Goals and Trade‑offs  
- **Distribution Transparency**: Hide access, location, failures.  
- **Openness**: Use standard interfaces and protocols.  
- **Scalability**: Performance must not degrade with growth.  
- **Trade‑offs**: Balancing transparency vs. performance; consistency vs. availability (CAP theorem implications, though not explicitly mentioned).  

### 3.5 Characteristics & Challenges  
- **Concurrent Execution**: Multiple processes run simultaneously.  
- **No Global Clock**: Asynchronous events; need logical clocks.  
- **Independent Failures**: Each node can fail unpredictably.  
- **Heterogeneity**: Diverse hardware, OS, network links.  
- **Security**: Protect data and communications.  

### 3.6 Types of Distributed Systems  
1. **Distributed Computing Systems** – Clusters, Grids.  
2. **Distributed Information Systems** – Transaction processing, Enterprise systems.  
3. **Distributed Pervasive Systems** – IoT, Smart homes.  

### 3.7 Architectural Models  
- **Client‑Server**:  
  - *Two‑tier*: Client + Server.  
  - *Three‑tier*: Client, Application server, Database server.  
  - *Multi‑tier (N‑tier)*: Additional layers (e.g., caching, load balancing).  
  - Example: Banking, university information systems.  
- **Peer‑to‑Peer (P2P)**:  
  - *Centralized*, *Decentralized*, *Hybrid*.  
  - Real‑world cases: BitTorrent, Skype.  
- **Service‑Oriented Architecture (SOA)** and **Microservices**:  
  - Decompose application into independent services.  
  - Case study: Netflix.  

### 3.8 Interprocess Communication (IPC)  
| IPC Method | Description |
|---|---|
| Message Passing | Sending data structures between processes. |
| Shared Memory | Processes read/write to common memory area. |
| Sockets & Ports | Network endpoints for TCP/UDP communication. |
| Synchronous vs. Asynchronous | Blocking vs. non‑blocking calls. |
| Remote Procedure Call (RPC) | Invoking procedures on remote machine. |
| Remote Method Invocation (RMI) | Java specific RPC. |
| Middleware | Software layer that abstracts IPC details. |

### 3.9 Synchronization  
- **Physical Clocks**: UTC, Clock drift, Skew → unreliable.  
- **Logical Clocks**:  
  - *Lamport Clocks*: Scalar counter, preserves causality.  
  - *Vector Clocks*: Capture causal relationships between events.  
- **Happened‑Before**: Partial order of events; essential for consistency.  

### 3.10 Concurrency Control  
- **ACID Properties**  
  - *Atomicity*: All or nothing.  
  - *Consistency*: Data remains valid.  
  - *Isolation*: No interference.  
  - *Durability*: Persisted changes survive failures.  
- **Concurrency Problems**  
  - Lost Update, Dirty Read, Inconsistent Retrieval.  
- **Control Mechanisms**  
  - Mutual Exclusion, Locks, Two‑Phase Locking (2PL), Deadlock detection/prevention.  

### 3.11 Distributed Algorithms & Consensus  
- **Failure Types**: Crash, Byzantine, etc.  
- **Election Algorithms**  
  - *Bully*: Highest ID wins.  
  - *Ring*: Pass token around ring.  
- **Consensus Protocols**  
  - *Paxos*: Reliable but complex.  
  - *Raft*: Leader‑based, easier to understand.  
  - *Gossip*: Spread information probabilistically.  

### 3.12 Lab Tools & Setup  
| Tool | Requirement |
|---|---|
| JDK 17+ | Yes |
| IntelliJ IDEA / NetBeans | Yes |
| Command Prompt / Terminal | Yes |
| Localhost Network | Yes |
| MySQL (for database labs) | Yes |
| MySQL Workbench | Helpful |
| Docker | Simulates multiple machines on one PC (optional) |

### 3.13 Lab Experiments Covered  
- Client‑Server communication, TCP socket programming, message passing, RPC/RMI, Lamport & vector clocks, leader election (Bully/Ring), mutual exclusion, distributed lock manager, concurrency control, load balancing, microservices simulation, failure detection.  

### 3.14 Assessment Structure  
| Component | Weight | Covered Lectures |
|---|---|---|
| Java programming (Sockets, RMI, Threads) | 10% | 1‑7 |
| Lab Assignments | 20% | 1‑7 |
| Midterm Exam | 60% | 1‑13 |
| Final Exam | 10% | Class activities, design project |
| Project / Participation | — | — |

### 3.15 References & Resources  
- **Primary Textbook**: *Distributed Systems: Concepts and Design* (5th Ed.) – Coulouris, Dollimore, Kindberg & Blair (2012).  
- **Secondary Textbook**: *Distributed Systems: Principles and Paradigms* (2nd Ed.) – Tanenbaum & Van Steen (2007).  

## 4. Key Terms and Definitions  

| Term | Definition |
|---|---|
| Distributed System | Networked collection of autonomous nodes sharing resources. |
| Node | Individual computer or process in the system. |
| Transparency | Hiding system complexity from users. |
| Scalability | Ability to grow with increased load. |
| Consistency | All nodes maintain identical data state. |
| Fault Tolerance | Ability to keep operating when failures occur. |
| Availability | System’s continuous responsiveness. |
| Client‑Server | Centralized model with distinct client and server tiers. |
| Peer‑to‑Peer | Decentralized model where nodes act as both client and server. |
| SOA | Architecture composed of loosely coupled services. |
| Microservices | Fine‑grained, independently deployable services. |
| IPC | Interprocess communication mechanisms. |
| RPC | Remote
