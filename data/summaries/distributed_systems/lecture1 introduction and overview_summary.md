# Lecture 1: Course Introduction and Overview

## 1. Lecture Overview  
This lecture introduces the **Distributed Systems** course. It defines what a distributed system is, explains why modern applications rely on multiple computers instead of a single powerful machine, and presents real‑world examples such as Google, Facebook, and cloud‑computing services. The lecture also outlines the course structure, learning objectives, assessment methods, required tools, and key references.

## 2. Learning Objectives  
By the end of this lecture you should be able to:  

1. **Define** a distributed system and identify its main components (nodes, processes, communication links, resource sharing).  
2. **Explain** the fundamental concepts of distributed systems: transparency, scalability, consistency, fault tolerance, and availability.  
3. **Recognize** the primary goals and design trade‑offs in building distributed systems.  
4. **Describe** the major characteristics and design challenges (concurrency, lack of a global clock, independent failures, heterogeneity, security, scalability, fault tolerance, QoS).  
5. **Differentiate** the three main types of distributed systems: Distributed Computing Systems, Distributed Information Systems, and Distributed Pervasive Systems.  
6. **Understand** the basic client‑server architecture and its tiered variants (two‑tier, three‑tier, N‑tier).  
7. **Identify** key inter‑process communication (IPC) mechanisms (message passing, shared memory, sockets, RPC, RMI) and the role of middleware.  
8. **Explain** physical vs. logical clocks, Lamport and vector clocks, and the “happened‑before” relationship.  
9. **Summarize** concurrency control concepts (ACID, locks, two‑phase locking, deadlocks).  
10. **Outline** election algorithms (Bully, Ring) and consensus protocols (Paxos, Raft, Gossip).  
11. **List** the tools and software required for the labs (JDK 17+, IntelliJ/NetBeans, Docker, MySQL, etc.).  
12. **Know** the assessment weights and project requirements.

## 3. Detailed Study Notes  

### 3.1 Definition of a Distributed System  
- A distributed system is a collection of **nodes** (computers) that **communicate** over a network to **share resources** and provide a **coherent service** to users.  
- Key components:  
  - **Nodes** – individual machines or processes.  
  - **Processes** – programs running on nodes.  
  - **Communication links** – network connections.  
  - **Resource sharing** – access to data, computation, storage, etc.

### 3.2 Why Use Multiple Computers?  
- Modern applications (e.g., Google search, Facebook social graph, cloud services) require **massive scalability**, **high availability**, and **fault tolerance** that a single machine cannot provide.  
- Distributed systems allow **parallel processing**, **load balancing**, and **redundancy**.

### 3.3 Core Concepts  
| Concept | What it means | Arabic explanation |
|---------|---------------|---------------------|
| **Transparency** | Hiding the complexity of the distributed system from users. | **الشفافية**: إخفاء تعقيد النظام الموزع عن المستخدمين. |
| **Scalability** | Ability to grow with more users or resources. | **قابلية التوسع**: قدرة النظام على النمو مع زيادة عدد المستخدمين أو الموارد. |
| **Consistency** | All servers present the same data view. | **التناسق**: جميع الخوادم تعرض نفس البيانات. |
| **Fault Tolerance** | System continues to operate despite failures. | **تحمل الأخطاء**: النظام يستمر في العمل رغم حدوث فشل. |
| **Availability** | System always responds to requests. | **التوافر**: النظام يرد دائمًا على الطلبات. |

### 3.4 Goals and Design Trade‑offs  
- **Accessibility**: Make resources available to all clients.  
- **Transparency**: Hide location, failure, and access details.  
- **Openness**: Allow integration with other systems.  
- **Scalability**: Support growth in users and data.  
- **Trade‑offs**: Enhancing one goal may reduce another (e.g., higher consistency can lower availability).

### 3.5 Characteristics & Design Challenges  
- **Concurrent execution** – multiple processes run simultaneously.  
- **No global clock** – nodes have independent clocks.  
- **Independent failures** – each node can fail without affecting others.  
- **Heterogeneity** – diverse hardware, OS, and network environments.  
- **Security** – authentication, authorization, data integrity.  
- **Fault tolerance** – mechanisms to detect and recover from failures.  
- **Quality of Service (QoS)** – performance guarantees.

### 3.6 Types of Distributed Systems  
1. **Distributed Computing Systems** – Clusters, Grids.  
2. **Distributed Information Systems** – Transaction processing, Enterprise systems.  
3. **Distributed Pervasive Systems** – IoT, Smart homes.

### 3.7 Distributed System Architectures  
- **Client‑Server**:  
  - **Two‑tier** – client + server.  
  - **Three‑tier** – client, application server, database server.  
  - **N‑tier** – multiple logical layers.  
  - Examples: banking systems, university portals.  
- **Peer‑to‑Peer (P2P)**: Centralized, Decentralized, Hybrid.  
- **Service‑Oriented Architecture (SOA)** and **Microservices**.  
  - Real‑world case studies: BitTorrent, Skype, Netflix.

### 3.8 Inter‑Process Communication (IPC)  
- **Message Passing** – explicit send/receive.  
- **Shared Memory** – concurrent access to shared data.  
- **Sockets & Ports** – network communication primitives.  
- **Synchronous vs. Asynchronous** – blocking vs. non‑blocking calls.  
- **Remote Procedure Call (RPC)** – client invokes server method.  
- **Remote Method Invocation (RMI)** – Java‑specific RPC.  
- **Middleware** – software layer that facilitates communication.

### 3.9 Synchronization & Clocks  
- **Physical Clocks** – UTC, Clock Drift, Skew.  
- **Logical Clocks** – Lamport clocks, Vector clocks.  
- **Happened‑Before** – causal ordering of events.  
- Purpose: maintain causality without a global clock.

### 3.10 Distributed Concurrency Control  
- **ACID Properties** – Atomicity, Consistency, Isolation, Durability.  
- **Concurrency Problems** – Lost Update, Dirty Read, Inconsistent Retrieval.  
- **Control Mechanisms** – Mutual Exclusion, Locks, Two‑Phase Locking (2PL), Deadlocks.

### 3.11 Distributed Algorithms  
- **Election Algorithms** – Bully, Ring.  
- **Consensus Protocols** – Paxos (reliable but complex), Raft (leader‑based, easier), Gossip (information spreading).  
- **Consensus** – all nodes agree on a single value.

### 3.12 Tools for Labs  
| Tool | Required? | Notes |
|------|-----------|-------|
| JDK 17+ | Yes | Java development |
| IntelliJ IDEA / NetBeans | Yes | IDE |
| Command Prompt / Terminal | Yes | For running programs |
| Localhost Network | Yes | Simulate multiple machines |
| MySQL | Yes (for database labs) | |
| MySQL Workbench | Helpful | Optional |
| Docker | Helpful | Simulates multiple machines on a single PC |

### 3.13 Lab Topics Covered  
- Client‑Server Communication  
- TCP Socket Programming  
- Message Passing  
- RPC Simulation  
- RMI  
- Lamport & Vector Clocks  
- Leader Election (Bully/Ring)  
- Mutual Exclusion & Distributed Lock Manager  
- Concurrency Control  
- Load Balancing  
- Microservices Simulation  
- Failure Detection  

### 3.14 References & Resources  
- **Primary Textbook**: Coulouris, G., Dollimore, J., Kindberg, T., & Blair, G. (2012). *Distributed Systems: Concepts and Design* (5th ed.). Addison‑Wesley.  
- **Secondary Textbook**: Tanenbaum, A. S., & Van Steen, M. (2007). *Distributed Systems: Principles and Paradigms* (2nd ed.). Pearson Prentice Hall.

### 3.15 Assessment Methods & Weights  
| Component | Weight |
|-----------|--------|
| Java programming (Sockets, RMI, Threads) | 10 % |
| Lab Assignments (Lectures 1‑7) | 20 % |
| Midterm Exam (Lectures 1‑13) | 60 % |
| Final Exam (class activities, discussions, design project) | 10 % |
| Project / Participation | Not specified in weight (included in final exam) |

## 4. Key Terms and Definitions  

- **Distributed System** – networked collection of nodes providing a unified service.  
- **Node** – individual computer or process.  
- **Transparency** – hiding system complexity from users.  
- **Scalability** – ability to handle growth.  
- **Consistency** – uniform data view across nodes.  
- **Fault Tolerance** – continued operation despite failures.  
- **Availability** – system responsiveness.  
- **Client‑Server Architecture** – tiered model of client and server interactions.  
- **Peer‑to‑Peer (P2P)** – decentralized node interactions.  
- **Service‑Oriented Architecture (SOA)** – modular services.  
- **Microservices** – fine‑grained, independently deployable services.  
- **IPC** – Inter‑Process Communication.  
- **Lamport Clock** – logical clock for event ordering.  
- **Vector Clock** – logical clock capturing causal relationships.  
- **ACID** – Atomicity, Consistency, Isolation, Durability.  
- **Two‑Phase Locking (2PL)** – locking protocol to ensure serializability.  
- **Election Algorithm** – process to select a leader node.  
- **Consensus Protocol** – agreement among distributed nodes.  

## 5. Examples Mentioned in the Lecture  
- **Google** – distributed search engine.  
- **Facebook** – distributed social network.  
- **Cloud Computing** – distributed infrastructure services.  
- **BitTorrent** – P2P file sharing.  
- **Skype** – P2P communication.  
- **Netflix** – microservices architecture.  
- **Banking systems** – example of three‑tier architecture.  
- **University systems** – example of tiered architecture.  

## 6. Important Course Information  
- **Course Title**: Distributed Systems  
- **Orientation**: Intro to distributed systems, real‑world examples.  
- **Tools**: JDK 17+, IntelliJ/NetBeans, Docker, MySQL, etc.  
- **References**: Coulouris et al. (5th ed.), Tanenbaum & Van Steen (2nd ed.).  
- **Assessment**: 10 % programming, 20 % labs, 60 % midterm, 10 % final.  

## 7. Revision Questions  

1. **Define a distributed system and list its main components.**  
2. **Explain the difference between physical and logical clocks, and why logical clocks are used in distributed systems.**  
3. **What are the five core concepts (transparency, scalability, consistency, fault tolerance, availability) and why are they important?**  
4. **Describe the two main types of IPC mechanisms mentioned in the lecture.**  
5. **What is the purpose of the ACID properties in distributed concurrency control?**  
6. **Compare the Bully and Ring election algorithms in terms of their operation.**  
7. **List the three main types of distributed systems and give one example for each.**  
8. **What are the assessment components of the course and their respective weights?**  

## 8. Answer Key  

1. **Answer**: A distributed system is a collection of networked nodes that communicate to share resources and provide a unified service. Main components: nodes, processes, communication links, and resource sharing.  
2. **Answer**: Physical clocks (UTC, drift, skew) are unreliable across machines; logical clocks (Lamport, vector) provide a causal ordering of events without a global clock.  
3. **Answer**:  
   - **Transparency**: hides complexity from users.  
   - **Scalability**: system can grow with more users/resources.  
   - **Consistency**: all nodes see the same data.  
   - **Fault tolerance**: system continues working after failures.  
   - **Availability**: system always responds.  
   These concepts ensure usability, reliability, and performance.  
4. **Answer**: Message passing (explicit send/receive) and shared memory (concurrent access to shared data).  
5. **Answer**: ACID ensures transactions are atomic, consistent, isolated, and durable, preventing data corruption and ensuring reliable concurrent access.  
6. **Answer**:  
   - **Bully**: highest‑ID node becomes leader; nodes send election messages.  
   - **Ring**: nodes arranged in a logical ring; election circulates a token.  
   Both elect a leader but differ in message patterns and assumptions.  
7. **Answer**:  
   - **Distributed Computing Systems** – e.g., clusters, grids.  
   - **Distributed Information Systems** – e.g., transaction processing, enterprise systems.  
   - **Distributed Pervasive Systems** – e.g., IoT, smart homes.  
8. **Answer**:  
   - Java programming: 10 %  
   - Lab assignments: 20 %  
   - Midterm exam: 60 %  
   - Final exam: 10 %  

## 9. Source Limitations  
- The lecture text lists objectives and topics but does **not** provide detailed explanations or examples for many concepts (e.g., specific implementation details of RPC, RMI, or consensus protocols).  
- Some slides mention “primary goals and design trade‑offs” without enumerating specific trade‑offs.  
- The assessment section lists weights but does not specify the exact content or format of the final project/participation component.  
- Tool descriptions are brief; configuration details (e.g., Docker usage) are not provided.  
- References are cited but page numbers or chapter specifics are missing, limiting precise location of material.
