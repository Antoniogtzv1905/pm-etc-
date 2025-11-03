from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from sqlalchemy import func
from .base_datos import inicializar_bd, obtener_sesion
from .models import User, Patient, Appointment, MedicalNote, VitalSign, Photo
from .esquemas import Token, UserCreate, UserOut, PatientCreate, PatientOut, AppointmentCreate, AppointmentOut, MedicalNoteCreate, MedicalNoteOut, VitalSignCreate, VitalSignOut, PhotoCreate, PhotoOut
from .auth import hash_password, verify_password, crear_token_acceso, obtener_usuario_actual

app = FastAPI(title="MedApp API", version="1.0.0", description="API del sistema MedApp para registro de pacientes y citas.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    inicializar_bd()

@app.get("/health", summary="Comprobar estado", tags=["Sistema"])
def estado():
    return {"status": "ok"}

@app.post("/auth/register", response_model=UserOut, summary="Registrar usuario", tags=["Autenticación"])
def registrar_usuario(usuario: UserCreate, session: Session = Depends(obtener_sesion)):
    existe = session.exec(select(User).where(User.email == usuario.email)).first()
    if existe:
        raise HTTPException(status_code=400, detail="Email ya registrado")
    usuario_model = User(name=usuario.name, email=usuario.email, password_hash=hash_password(usuario.password))
    session.add(usuario_model)
    session.commit()
    session.refresh(usuario_model)
    return UserOut(id=usuario_model.id, name=usuario_model.name, email=usuario_model.email)

@app.post("/auth/login", response_model=Token, summary="Iniciar sesión", tags=["Autenticación"])
def iniciar_sesion(form: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(obtener_sesion)):
    usuario = session.exec(select(User).where(User.email == form.username)).first()
    if not usuario or not verify_password(form.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token = crear_token_acceso({"sub": str(usuario.id)})
    return Token(access_token=token)

@app.get("/patients", response_model=List[PatientOut], summary="Listar pacientes", tags=["Pacientes"])
def listar_pacientes(search: Optional[str] = None, usuario: User = Depends(obtener_usuario_actual), session: Session = Depends(obtener_sesion)):
    query = select(Patient)
    if search:
        query = query.where(func.lower(Patient.name).like(f"%{search.lower()}%"))
    return session.exec(query).all()

@app.post("/patients", response_model=PatientOut, summary="Crear paciente", tags=["Pacientes"])
def crear_paciente(p: PatientCreate, usuario: User = Depends(obtener_usuario_actual), session: Session = Depends(obtener_sesion)):
    paciente = Patient(**p.dict())
    session.add(paciente)
    session.commit()
    session.refresh(paciente)
    return PatientOut(**paciente.dict())

@app.get("/patients/{pid}", response_model=PatientOut, summary="Obtener paciente", tags=["Pacientes"])
def obtener_paciente(pid: int, usuario: User = Depends(obtener_usuario_actual), session: Session = Depends(obtener_sesion)):
    paciente = session.get(Patient, pid)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return PatientOut(**paciente.dict())

@app.put("/patients/{pid}", response_model=PatientOut, summary="Actualizar paciente", tags=["Pacientes"])
def actualizar_paciente(pid: int, p: PatientCreate, usuario: User = Depends(obtener_usuario_actual), session: Session = Depends(obtener_sesion)):
    paciente = session.get(Patient, pid)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    for k, v in p.dict().items():
        setattr(paciente, k, v)
    session.add(paciente)
    session.commit()
    session.refresh(paciente)
    return PatientOut(**paciente.dict())

@app.delete("/patients/{pid}", summary="Eliminar paciente", tags=["Pacientes"])
def eliminar_paciente(pid: int, usuario: User = Depends(obtener_usuario_actual), session: Session = Depends(obtener_sesion)):
    paciente = session.get(Patient, pid)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    session.delete(paciente)
    session.commit()
    return {"ok": True}

@app.get("/patients/{pid}/appointments", response_model=List[AppointmentOut], summary="Listar citas", tags=["Citas"])
def listar_citas(pid: int, usuario: User = Depends(obtener_usuario_actual), session: Session = Depends(obtener_sesion)):
    return session.exec(select(Appointment).where(Appointment.patient_id == pid)).all()

@app.post("/patients/{pid}/appointments", response_model=AppointmentOut, summary="Crear cita", tags=["Citas"])
def crear_cita(pid: int, ap: AppointmentCreate, usuario: User = Depends(obtener_usuario_actual), session: Session = Depends(obtener_sesion)):
    if not session.get(Patient, pid):
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    cita = Appointment(patient_id=pid, **ap.dict())
    session.add(cita)
    session.commit()
    session.refresh(cita)
    return AppointmentOut(**cita.dict())

@app.put("/appointments/{aid}", response_model=AppointmentOut, summary="Actualizar cita", tags=["Citas"])
def actualizar_cita(aid: int, ap: AppointmentCreate, usuario: User = Depends(obtener_usuario_actual), session: Session = Depends(obtener_sesion)):
    cita = session.get(Appointment, aid)
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    for k, v in ap.dict().items():
        setattr(cita, k, v)
    session.add(cita)
    session.commit()
    session.refresh(cita)
    return AppointmentOut(**cita.dict())

@app.delete("/appointments/{aid}", summary="Eliminar cita", tags=["Citas"])
def eliminar_cita(aid: int, usuario: User = Depends(obtener_usuario_actual), session: Session = Depends(obtener_sesion)):
    cita = session.get(Appointment, aid)
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    session.delete(cita)
    session.commit()
    return {"ok": True}
