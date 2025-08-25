// Fluid Animation System - Exact replica of Devarshi's portfolio
class FluidAnimation {
    constructor() {
        this.canvas = document.getElementById('fluidCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.mouse = { x: 0, y: 0 };
        this.animationId = null;
        
        // Animation settings matching the original
        this.particleCount = 120;
        this.connectionDistance = 100;
        this.mouseInfluence = 150;
        
        this.init();
        this.setupEventListeners();
        this.animate();
    }
    
    init() {
        this.resizeCanvas();
        this.createParticles();
    }
    
    resizeCanvas() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }
    
    createParticles() {
        this.particles = [];
        for (let i = 0; i < this.particleCount; i++) {
            this.particles.push(new Particle(this.canvas.width, this.canvas.height));
        }
    }
    
    setupEventListeners() {
        window.addEventListener('resize', () => {
            this.resizeCanvas();
            this.createParticles();
        });
        
        window.addEventListener('mousemove', (e) => {
            this.mouse.x = e.clientX;
            this.mouse.y = e.clientY;
        });
        
        // Touch events for mobile
        window.addEventListener('touchmove', (e) => {
            if (e.touches[0]) {
                this.mouse.x = e.touches[0].clientX;
                this.mouse.y = e.touches[0].clientY;
            }
        });
    }
    
    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Update particles
        this.particles.forEach(particle => {
            particle.update(this.mouse, this.mouseInfluence);
            particle.draw(this.ctx);
        });
        
        // Draw connections
        this.drawConnections();
        
        this.animationId = requestAnimationFrame(() => this.animate());
    }
    
    drawConnections() {
        for (let i = 0; i < this.particles.length; i++) {
            for (let j = i + 1; j < this.particles.length; j++) {
                const dx = this.particles[i].x - this.particles[j].x;
                const dy = this.particles[i].y - this.particles[j].y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < this.connectionDistance) {
                    const opacity = (this.connectionDistance - distance) / this.connectionDistance;
                    
                    this.ctx.save();
                    this.ctx.globalAlpha = opacity * 0.3;
                    this.ctx.strokeStyle = '#4ea1ff';
                    this.ctx.lineWidth = 1;
                    this.ctx.beginPath();
                    this.ctx.moveTo(this.particles[i].x, this.particles[i].y);
                    this.ctx.lineTo(this.particles[j].x, this.particles[j].y);
                    this.ctx.stroke();
                    this.ctx.restore();
                }
            }
        }
    }
    
    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
    }
}

class Particle {
    constructor(canvasWidth, canvasHeight) {
        this.x = Math.random() * canvasWidth;
        this.y = Math.random() * canvasHeight;
        this.vx = (Math.random() - 0.5) * 0.8;
        this.vy = (Math.random() - 0.5) * 0.8;
        this.size = Math.random() * 3 + 1;
        this.baseSize = this.size;
        this.alpha = Math.random() * 0.5 + 0.3;
        this.baseAlpha = this.alpha;
        
        // Color variations
        const colors = [
            '#4ea1ff',
            '#a855f7',
            '#06b6d4',
            '#8b5cf6',
            '#3b82f6'
        ];
        this.color = colors[Math.floor(Math.random() * colors.length)];
        
        this.canvasWidth = canvasWidth;
        this.canvasHeight = canvasHeight;
    }
    
    update(mouse, mouseInfluence) {
        // Basic movement
        this.x += this.vx;
        this.y += this.vy;
        
        // Boundary collision
        if (this.x < 0 || this.x > this.canvasWidth) {
            this.vx *= -1;
            this.x = Math.max(0, Math.min(this.canvasWidth, this.x));
        }
        if (this.y < 0 || this.y > this.canvasHeight) {
            this.vy *= -1;
            this.y = Math.max(0, Math.min(this.canvasHeight, this.y));
        }
        
        // Mouse interaction
        const dx = mouse.x - this.x;
        const dy = mouse.y - this.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < mouseInfluence) {
            const force = (mouseInfluence - distance) / mouseInfluence;
            const angle = Math.atan2(dy, dx);
            
            // Attraction to mouse
            this.vx += Math.cos(angle) * force * 0.02;
            this.vy += Math.sin(angle) * force * 0.02;
            
            // Increase size and alpha near mouse
            this.size = this.baseSize + force * 2;
            this.alpha = Math.min(1, this.baseAlpha + force * 0.5);
        } else {
            // Return to normal size and alpha
            this.size += (this.baseSize - this.size) * 0.1;
            this.alpha += (this.baseAlpha - this.alpha) * 0.1;
        }
        
        // Velocity damping
        this.vx *= 0.99;
        this.vy *= 0.99;
        
        // Limit velocity
        const maxVelocity = 2;
        this.vx = Math.max(-maxVelocity, Math.min(maxVelocity, this.vx));
        this.vy = Math.max(-maxVelocity, Math.min(maxVelocity, this.vy));
    }
    
    draw(ctx) {
        ctx.save();
        ctx.globalAlpha = this.alpha;
        
        // Create gradient for particle
        const gradient = ctx.createRadialGradient(
            this.x, this.y, 0,
            this.x, this.y, this.size * 2
        );
        gradient.addColorStop(0, this.color);
        gradient.addColorStop(1, 'transparent');
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fill();
        
        // Add glow effect
        ctx.shadowColor = this.color;
        ctx.shadowBlur = 10;
        ctx.fillStyle = this.color;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size * 0.5, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.restore();
    }
}

// Navigation System
class Navigation {
    constructor() {
        this.navItems = document.querySelectorAll('.nav-item');
        this.contentSections = document.querySelectorAll('.content-section');
        this.titleElement = document.getElementById('dynamicTitle');
        
        this.titles = {
            'me': 'GenAI Developer',
            'experience': 'Machine Learning Engineer',
            'projects': 'Full Stack Developer',
            'skills': 'Data Scientist',
            'contact': 'Tech Enthusiast'
        };
        
        this.setupNavigation();
    }
    
    setupNavigation() {
        this.navItems.forEach(item => {
            item.addEventListener('click', () => {
                const section = item.dataset.section;
                this.switchSection(section);
            });
        });
    }
    
    switchSection(sectionId) {
        // Update navigation
        this.navItems.forEach(item => {
            item.classList.remove('active');
            if (item.dataset.section === sectionId) {
                item.classList.add('active');
            }
        });
        
        // Update content
        this.contentSections.forEach(section => {
            section.classList.remove('active');
            if (section.id === sectionId) {
                section.classList.add('active');
            }
        });
        
        // Update title with animation
        this.animateTitle(this.titles[sectionId] || 'GenAI Developer');
    }
    
    animateTitle(newTitle) {
        this.titleElement.style.opacity = '0';
        this.titleElement.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            this.titleElement.textContent = newTitle;
            this.titleElement.style.opacity = '1';
            this.titleElement.style.transform = 'translateY(0)';
        }, 200);
    }
}

// Chat System
class ChatSystem {
    constructor() {
        this.chatInput = document.querySelector('.chat-input');
        this.sendBtn = document.querySelector('.chat-send-btn');
        
        this.responses = [
            "That's an interesting question! I'd love to discuss that with you.",
            "Great point! My experience in AI development has taught me a lot about that.",
            "I'm passionate about solving complex problems like that one.",
            "Technology is fascinating, isn't it? I enjoy exploring new possibilities.",
            "Thanks for asking! I'm always excited to share my knowledge."
        ];
        
        this.setupChat();
    }
    
    setupChat() {
        this.sendBtn.addEventListener('click', () => this.handleSend());
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleSend();
            }
        });
        
        // Typing animation
        this.chatInput.addEventListener('input', () => {
            this.animateTyping();
        });
    }
    
    handleSend() {
        const message = this.chatInput.value.trim();
        if (message) {
            this.simulateResponse();
            this.chatInput.value = '';
        }
    }
    
    simulateResponse() {
        const response = this.responses[Math.floor(Math.random() * this.responses.length)];
        
        // Create temporary response display
        const responseDiv = document.createElement('div');
        responseDiv.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(78, 161, 255, 0.9);
            color: white;
            padding: 1rem 2rem;
            border-radius: 10px;
            z-index: 1000;
            animation: fadeInUp 0.3s ease-out;
        `;
        responseDiv.textContent = response;
        document.body.appendChild(responseDiv);
        
        setTimeout(() => {
            responseDiv.style.animation = 'fadeOut 0.3s ease-out forwards';
            setTimeout(() => responseDiv.remove(), 300);
        }, 3000);
    }
    
    animateTyping() {
        this.chatInput.style.transform = 'scale(1.02)';
        setTimeout(() => {
            this.chatInput.style.transform = 'scale(1)';
        }, 100);
    }
}

// Particle Trail Effect
class ParticleTrail {
    constructor() {
        this.trails = [];
        this.setupTrail();
    }
    
    setupTrail() {
        document.addEventListener('mousemove', (e) => {
            if (Math.random() < 0.3) { // Reduce frequency
                this.createTrailParticle(e.clientX, e.clientY);
            }
        });
        
        this.animateTrails();
    }
    
    createTrailParticle(x, y) {
        const particle = {
            x: x,
            y: y,
            vx: (Math.random() - 0.5) * 2,
            vy: (Math.random() - 0.5) * 2,
            life: 1,
            decay: 0.02,
            size: Math.random() * 3 + 1,
            color: `hsl(${220 + Math.random() * 40}, 70%, 60%)`
        };
        
        this.trails.push(particle);
        
        // Limit trail particles
        if (this.trails.length > 50) {
            this.trails.shift();
        }
    }
    
    animateTrails() {
        const canvas = document.getElementById('fluidCanvas');
        const ctx = canvas.getContext('2d');
        
        // This will be called within the main animation loop
        this.trails.forEach((particle, index) => {
            particle.x += particle.vx;
            particle.y += particle.vy;
            particle.life -= particle.decay;
            particle.size *= 0.98;
            
            if (particle.life <= 0 || particle.size < 0.1) {
                this.trails.splice(index, 1);
                return;
            }
            
            ctx.save();
            ctx.globalAlpha = particle.life * 0.5;
            ctx.fillStyle = particle.color;
            ctx.beginPath();
            ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        });
        
        requestAnimationFrame(() => this.animateTrails());
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize fluid animation
    const fluidAnimation = new FluidAnimation();
    
    // Initialize navigation
    const navigation = new Navigation();
    
    // Initialize chat system
    const chatSystem = new ChatSystem();
    
    // Initialize particle trail
    const particleTrail = new ParticleTrail();
    
    // Add some interactive effects
    document.querySelectorAll('.nav-item, .project-card, .skill-item').forEach(element => {
        element.addEventListener('mouseenter', () => {
            element.style.transform += ' scale(1.05)';
        });
        
        element.addEventListener('mouseleave', () => {
            element.style.transform = element.style.transform.replace(' scale(1.05)', '');
        });
    });
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        fluidAnimation.destroy();
    });
    
    console.log('🎨 Fluid Portfolio Animation System Initialized');
});